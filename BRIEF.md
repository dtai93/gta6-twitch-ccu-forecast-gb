# make.fun bounty: gta6-twitch-ccu-forecast-01

Build a Python 3.13 entry (stdlib only) that forecasts Twitch concurrent viewers for GTA VI launch day.

## Deliverables in this repo root
- main.py — the program the grader runs: `python3 -P -s /bot/main.py`
- LICENSE — MIT with SPDX-License-Identifier: MIT
- README.md — must include these three badge lines exactly (replace nothing else about badges):

```
[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/dtai93/gta6-twitch-ccu-forecast-gb/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/dtai93/gta6-twitch-ccu-forecast-gb/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
```

- .makefun/owner.json — `{"wallet":"GnrY9jpLCQ5i8oEucgVvuHCe4asnKT8t6cT8kbejhoto"}`

## Behavior of main.py
- Read every `*.in` from MAKEFUN_INPUT_DIR (default /input)
- Write `*.out` to MAKEFUN_OUTPUT_DIR (default /output)
- Input schema makefun/twitch-ccu-case/v1: known hour-1 viewers, forecast hours 2..24, history, history_hourly, comparables with hourly launch curves
- Output: `{"hours":[{"hour":2,"q":[q05,q25,q50,q75,q95]}, ...]}` exactly 23 rows, q nondecreasing, each in (0, 1e9]
- No network. Stdlib only.
- Score = mean pinball loss on log scale; lower better. Beat persistence baseline.

## Strategy hint
Use weighted log-space shapes from `comparables` day-of-launch hours relative to each comparable's hour-1, blend with mild persistence, shrink tails for pinball. Prefer big open-world / Rockstar-like comps when present.

## Workflow
1. Read RULES and starter at the kit path given in the prompt (add-dir).
2. Implement main.py, then improve it at least once after a smoke test on practice inputs.
3. Add LICENSE, README badges, .makefun/owner.json.
4. Do not copy starter main.py verbatim; write your own forecast logic.

Practice smoke test:
```
mkdir -p /tmp/gta-out && MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=/tmp/gta-out python3 main.py
```
