from pathlib import Path

def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly 1 match, found {count}. No files written."
        )
    return source.replace(old, new, 1)

rw_path = Path("services/api/app/real_world.py")
main_path = Path("services/api/app/main.py")

rw = rw_path.read_text(encoding="utf-8")
main = main_path.read_text(encoding="utf-8")

# Historical data function
rw = replace_once(
    rw,
    "if interval < 1 or interval > 15:",
    "if interval < 1 or interval > 300:",
    "Historical interval validation"
)

rw = replace_once(
    rw,
    "        else end - timedelta(days=28)",
    "        else end - timedelta(days=28 if interval <= 15 else 89)",
    "Default historical date range"
)

rw = replace_once(
    rw,
    "    if (end - start).days > 30:\n"
    "        raise ValueError(\n"
    '            "Request no more than one month of 1-15 minute candles."\n'
    "        )",
    "    max_days = 30 if interval <= 15 else 90\n"
    "    if (end - start).days > max_days:\n"
    "        raise ValueError(\n"
    '            "Request no more than 30 days for 1-15 minute candles."\n'
    "            if interval <= 15\n"
    '            else "Request no more than 90 days for intervals above 15 minutes."\n'
    "        )",
    "Historical date-range validation"
)

# API route
main = replace_once(
    main,
    "interval: int = Query(5, ge=1, le=15), cost_bps: float = Query(10.0, ge=0, le=100),",
    "interval: int = Query(5, ge=1, le=300), folds: int = Query(3, ge=2, le=5),\n"
    "                      cost_bps: float = Query(10.0, ge=0, le=100),",
    "API query parameters"
)

main = replace_once(
    main,
    "if normalized_interval not in {1, 2, 3, 5, 10, 15}:",
    "if normalized_interval not in {1, 2, 3, 5, 10, 15, 30}:",
    "Allowed candle intervals"
)

main = replace_once(
    main,
    'raise ValueError("Interval must be 1, 2, 3, 5, 10 or 15 minutes.")',
    'raise ValueError("Interval must be 1, 2, 3, 5, 10, 15 or 30 minutes.")',
    "Interval error message"
)

main = replace_once(
    main,
    "evaluation = walk_forward_intraday(engineered, folds=3, cost_bps=cost_bps)",
    "evaluation = walk_forward_intraday(engineered, folds=folds, cost_bps=cost_bps)",
    "Configurable walk-forward folds"
)

# Write only after every expected replacement has succeeded.
rw_path.write_text(rw, encoding="utf-8")
main_path.write_text(main, encoding="utf-8")

print("SUCCESS: 30-minute research support added.")
print("Existing 1-15 minute default remains 28 days.")
print("Intervals above 15 minutes: up to 90 calendar days.")
print("Walk-forward folds: configurable from 2 to 5; default 3.")
