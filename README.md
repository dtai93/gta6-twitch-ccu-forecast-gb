# GTA VI Twitch CCU forecast

Forecasts Twitch concurrent viewers for a launch day, hours 2 through 24, after hour 1 is known. Comparable launch curves are weighted in log space toward big open-world titles, blended with a mild persistence pull, and wrapped in pinball-aware quantile bands.

## Run it

```bash
mkdir -p /tmp/gta-out
MAKEFUN_INPUT_DIR=/path/to/input MAKEFUN_OUTPUT_DIR=/tmp/gta-out python3 main.py
```

Python 3.13, standard library only. Every `*.in` in `MAKEFUN_INPUT_DIR` (default `/input`) produces `<id>.out` in `MAKEFUN_OUTPUT_DIR` (default `/output`).

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/dtai93/gta6-twitch-ccu-forecast-gb/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/dtai93/gta6-twitch-ccu-forecast-gb/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

---

[make.fun](https://make.fun/?ref=57606m4t)
