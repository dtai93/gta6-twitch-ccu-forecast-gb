"""Launch-day Twitch CCU forecast for hours 2..24.

Comparables vote in log space. Each past launch is scaled to its own pre-midnight
peak, then placed on this case's hour-1 print. Big open-world and console
single-player titles count more, nearer pre-launch paths count more, and the
median is pulled slightly toward a flat hour-1 (persistence). Quantile bands use
a shrunk weighted spread so a few explosive launches do not set the tails.
"""

import json
import math
import os
from datetime import datetime
from pathlib import Path

LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
Z_SCORES = (-1.645, -0.674, 0.0, 0.674, 1.645)

# How strongly a title resembles a big open-world / Rockstar-style launch.
GENRE_WEIGHTS = (
    ("elden ring nightreign", 1.3),
    ("elden ring", 3.2),
    ("red dead", 5.5),
    ("god of war", 3.8),
    ("wolverine", 3.2),
    ("spider-man", 3.4),
    ("ghost of yōtei", 4.4),
    ("ghost of yotei", 4.4),
    ("ghost of tsushima", 4.2),
    ("cyberpunk", 2.8),
    ("hogwarts", 2.2),
    ("zelda", 3.0),
    ("starfield", 1.8),
    ("kingdom come", 1.8),
    ("assassin", 2.0),
    ("death stranding", 1.8),
    ("last of us", 3.8),
    ("final fantasy vii", 2.4),
    ("stellar blade", 3.4),
    ("resident evil", 2.2),
    ("monster hunter", 1.8),
    ("black myth", 1.2),
    ("baldur", 1.3),
    ("clair obscur", 1.6),
    ("borderlands", 1.6),
    ("forza", 1.0),
    ("diablo", 0.9),
    ("doom", 0.7),
    ("halo", 0.45),
    ("call of duty", 0.85),
    ("battlefield", 0.3),
    ("helldivers", 0.2),
    ("marvel rivals", 0.2),
    ("arc raiders", 0.25),
    ("marathon", 0.25),
    ("007", 1.3),
    ("saros", 1.8),
    ("hollow knight", 0.35),
)

PERSIST = 0.05
PATH_TAU = 0.45
PRER_TAU = 0.45
SIZE_TAU = 1.15
PRIOR_SIGMA = 0.42
SIGMA_MULT = 0.9
SIGMA_FLOOR = 0.12
SIGMA_CAP = 0.85
# Pinball charges more for a low upper quantile than a high one, so the
# upper tail stays wider than the lower tail.
UPPER_TAIL = 1.25
LOWER_TAIL = 0.80
SHRINK_K = 5.0
LOG_CLIP = 2.4
MIN_COMP_H1 = 5000.0
MAX_BASE_RATIO = 0.20
REGIME_PENALTY = 0.40
MIN_Q = 0.01
MAX_Q = 1_000_000_000.0


def parse_time(text):
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def round2(value):
    """Two decimals, half up, so two runs write the same bytes."""
    scaled = float(value) * 100.0
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    return whole / 100.0


def index_hours(rows, origin):
    origin_dt = parse_time(origin)
    indexed = {}
    for row in rows or []:
        stamp = row.get("from")
        if not stamp or row.get("viewers") is None:
            continue
        delta = (parse_time(stamp) - origin_dt).total_seconds() / 3600.0
        hour = round(delta)
        if abs(delta - hour) > 1e-3:
            continue
        indexed[int(hour)] = float(row["viewers"])
    return indexed


def genre_weight(name, unlock, platforms):
    label = (name or "").lower()
    note = (unlock or "").lower()
    plats = (platforms or "").lower()
    if "grand theft auto" in label or "not a launch" in note or "target-history" in note:
        return 0.0
    weight = 1.0
    for key, value in GENRE_WEIGHTS:
        if key in label:
            weight = value
            break
    if "early-access" in note:
        weight *= 0.30
    if "tier: weak" in note:
        weight *= 0.22
    console = any(token in plats for token in ("ps", "xbox", "switch"))
    if console and "pc" not in plats:
        weight *= 1.25
    return weight


def launch_profile(series, hour1):
    hour1 = max(float(hour1), 1.0)
    present = [series[k] for k in range(-16, 0) if k in series]
    if len(present) < 8:
        return None
    peak = max(present)
    baseline_values = [series[k] for k in range(-48, -24) if k in series]
    if baseline_values:
        baseline = sorted(baseline_values)[len(baseline_values) // 2]
    else:
        baseline = 0.0
    path = {}
    for offset in range(-12, 0):
        if offset in series:
            path[offset] = math.log(max(series[offset], 1.0)) - math.log(hour1)
    last = series.get(-1)
    return {
        "peak": peak,
        "pre_ratio": peak / hour1,
        "base_ratio": baseline / hour1,
        "last_ratio": (last / hour1) if last is not None else None,
        "path": path,
    }


def build_library(comparables):
    library = []
    for comp in comparables or []:
        series = index_hours(comp.get("hourly"), comp.get("day_start"))
        hour1 = series.get(0, 0.0)
        profile = launch_profile(series, hour1) if hour1 > 0 else None
        library.append(
            {
                "name": comp.get("name") or "",
                "series": series,
                "hour1": hour1,
                "profile": profile,
                "genre": genre_weight(comp.get("name"), comp.get("unlock"), comp.get("platforms")),
            }
        )
    return library


def neighbor_weights(target, library):
    profile = target["profile"]
    hour1 = target["hour1"]
    weighted = []
    for comp in library:
        other = comp["profile"]
        if other is None or comp["genre"] <= 0 or comp["hour1"] < MIN_COMP_H1:
            continue
        if other["base_ratio"] > MAX_BASE_RATIO:
            continue
        shared = [k for k in profile["path"] if k in other["path"]]
        if len(shared) < 6:
            continue
        sq = sum((profile["path"][k] - other["path"][k]) ** 2 for k in shared)
        rmse = math.sqrt(sq / len(shared))
        sim = math.exp(-(rmse * rmse) / (2.0 * PATH_TAU * PATH_TAU))
        pre_gap = math.log(max(other["pre_ratio"], 1e-3)) - math.log(max(profile["pre_ratio"], 1e-3))
        sim *= math.exp(-(pre_gap * pre_gap) / (2.0 * PRER_TAU * PRER_TAU))
        size_gap = math.log(comp["hour1"]) - math.log(hour1)
        sim *= math.exp(-(size_gap * size_gap) / (2.0 * SIZE_TAU * SIZE_TAU))
        regime = 1.0
        if profile["last_ratio"] is not None and other["last_ratio"] is not None:
            target_falling = profile["last_ratio"] >= 1.05
            comp_falling = other["last_ratio"] >= 1.05
            if target_falling and other["last_ratio"] < 0.98:
                regime = REGIME_PENALTY
            elif (not target_falling) and profile["last_ratio"] < 0.98 and comp_falling and other["last_ratio"] > 1.25:
                regime = REGIME_PENALTY
        weight = comp["genre"] * sim * regime * math.log10(max(comp["hour1"], 10.0))
        if weight > 0:
            weighted.append((weight, comp))
    return weighted


def log_ratio(target, comp, offset):
    viewers = comp["series"].get(offset)
    if viewers is None or viewers <= 0 or comp["hour1"] <= 0:
        return None
    comp_peak = comp["profile"]["peak"] if comp["profile"] else 0.0
    target_peak = target["profile"]["peak"]
    if target_peak > 0 and comp_peak > 0:
        level = target_peak * (viewers / comp_peak)
        ratio = math.log(max(level, 1e-9)) - math.log(target["hour1"])
    else:
        ratio = math.log(viewers) - math.log(comp["hour1"])
    if ratio > LOG_CLIP:
        return LOG_CLIP
    if ratio < -LOG_CLIP:
        return -LOG_CLIP
    return ratio


def weighted_median(pairs):
    ordered = sorted(pairs, key=lambda item: (item[0], item[2]))
    total = sum(weight for _, weight, _ in ordered)
    if total <= 0:
        return None
    walked = 0.0
    for value, weight, _ in ordered:
        walked += weight
        if walked >= 0.5 * total:
            return value
    return ordered[-1][0]


def hour_center_and_scale(target, neighbors, offset):
    pairs = []
    for weight, comp in neighbors:
        ratio = log_ratio(target, comp, offset)
        if ratio is None:
            continue
        pairs.append((ratio, weight, comp["name"]))
    raw_median = weighted_median(pairs)
    if raw_median is None:
        return 0.0, 0.15 * math.sqrt(offset)
    total = sum(weight for _, weight, _ in pairs)
    second = sum(weight * weight for _, weight, _ in pairs)
    variance = sum(weight * (value - raw_median) ** 2 for value, weight, _ in pairs) / total
    n_eff = (total * total / second) if second > 0 else 1.0
    shrink = n_eff / (n_eff + SHRINK_K)
    sigma = math.sqrt(shrink * variance + (1.0 - shrink) * PRIOR_SIGMA * PRIOR_SIGMA)
    sigma = SIGMA_MULT * sigma
    if sigma < SIGMA_FLOOR:
        sigma = SIGMA_FLOOR
    if sigma > SIGMA_CAP:
        sigma = SIGMA_CAP
    # Mild pull toward "hour 1 repeats" so a thin neighbor set cannot run away.
    return (1.0 - PERSIST) * raw_median, sigma


def persistence_band(hour):
    return 0.0, 0.18 * math.sqrt(hour - 1)


def quantile_row(hour, hour1, center, sigma):
    last = MIN_Q
    quantiles = []
    for z in Z_SCORES:
        if z > 0:
            scale = sigma * UPPER_TAIL
        elif z < 0:
            scale = sigma * LOWER_TAIL
        else:
            scale = sigma
        raw = hour1 * math.exp(center + z * scale)
        if not math.isfinite(raw) or raw <= 0:
            raw = hour1
        raw = min(MAX_Q, max(raw, MIN_Q))
        value = round2(raw)
        if value < MIN_Q:
            value = MIN_Q
        if value > MAX_Q:
            value = MAX_Q
        if value < last:
            value = last
        quantiles.append(value)
        last = value
    return {"hour": hour, "q": quantiles}


def hour1_of(case):
    for row in case.get("known") or []:
        if row.get("hour") == 1 and row.get("viewers") is not None:
            return max(1.0, float(row["viewers"]))
    return 1.0


def forecast_case(case):
    hour1 = hour1_of(case)
    series = index_hours(case.get("history_hourly"), case.get("day_start"))
    series[0] = hour1
    target = {"hour1": hour1, "profile": launch_profile(series, hour1), "series": series}
    library = build_library(case.get("comparables"))
    neighbors = neighbor_weights(target, library) if target["profile"] is not None else []
    rows = []
    for hour in range(2, 25):
        if neighbors:
            center, sigma = hour_center_and_scale(target, neighbors, hour - 1)
        else:
            center, sigma = persistence_band(hour)
        rows.append(quantile_row(hour, hour1, center, sigma))
    return {"hours": rows}


def main():
    in_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(in_dir.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        payload = forecast_case(case)
        text = json.dumps(payload, separators=(",", ":")) + "\n"
        (out_dir / f"{path.stem}.out").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
