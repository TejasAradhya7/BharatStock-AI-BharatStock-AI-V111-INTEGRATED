#!/usr/bin/env python3
"""Run a real-data walk-forward model evaluation using configured Upstox access.

Run from repository root:
  python scripts/run_model_evaluation.py --instrument-key "NSE_EQ|INE002A01018" --symbol RELIANCE.NS

The script writes reports/model_evaluation.json and reports/model_folds.csv.
It never creates synthetic market data. If the provider returns too few candles,
it exits with an explicit message instead of inventing a score.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "services" / "api"
sys.path.insert(0, str(API_DIR))
try:
    from dotenv import load_dotenv
    load_dotenv(API_DIR / ".env")
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app.real_world import (
    fetch_upstox_historical,
    fetch_upstox_news,
    build_intraday_features,
    walk_forward_intraday,
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument-key", required=True, help='Exact Upstox instrument key, e.g. "NSE_EQ|INE002A01018"')
    parser.add_argument("--symbol", default="RELIANCE.NS")
    parser.add_argument("--interval", type=int, default=5, choices=[1,2,3,5,10,15])
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument(
        "--from-date",
        default=None,
        help="Historical start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--to-date",
        default=None,
        help="Historical end date in YYYY-MM-DD format",
    )
    parser.add_argument("--cost-bps", type=float, default=10.0, help="Estimated cost per side in basis points; replace with your real cost schedule")
    args = parser.parse_args()
    if not os.getenv("UPSTOX_ACCESS_TOKEN", "").strip():
        raise SystemExit("ERROR: UPSTOX_ACCESS_TOKEN is missing. Set it in services/api/.env. Never put the token in source code or share it.")
    outdir = ROOT / "reports"
    outdir.mkdir(exist_ok=True)
    market = fetch_upstox_historical(
        instrument_key=args.instrument_key,
        interval=args.interval,
        from_date=args.from_date,
        to_date=args.to_date,
    )
    candles = pd.DataFrame(market["candles"])
    candles["timestamp"] = pd.to_datetime(candles["timestamp"], utc=True, errors="coerce")
    # Best-effort news fetch; no headlines is reported, not silently treated as historical coverage.
    news_meta = {"provider":"Upstox News API", "count":0, "status":"unavailable"}
    events = []
    try:
        n = fetch_upstox_news([args.instrument_key])
        events = n.get("articles", [])
        news_meta = {"provider": n.get("provider"), "count":len(events),
                     "fetched_at":n.get("fetched_at"), "history_limit":n.get("history_limit"),
                     "status":"loaded" if events else "no timestamped articles returned"}
    except Exception as exc:
        news_meta = {"provider":"Upstox News API", "count":0, "status":"fetch failed",
                     "error":f"{type(exc).__name__}: {str(exc)[:240]}"}
    # Walk-forward historical scores are built from market-candle features only unless
    # a true point-in-time news archive with available_at timestamps is available.
    # Recent news is recorded in the report but not backfilled into old candles.
    features = build_intraday_features(candles)
    result = walk_forward_intraday(features, folds=args.folds, cost_bps=args.cost_bps)
    report = {
        "project":"BharatStock AI",
        "symbol":args.symbol,
        "provider":market.get("provider"),
        "instrument_key":args.instrument_key,
        "interval_minutes":args.interval,
        "fetched_at":market.get("fetched_at"),
        "observations_received":int(len(candles)),
        "timestamp_start":str(candles["timestamp"].min()) if len(candles) else None,
        "timestamp_end":str(candles["timestamp"].max()) if len(candles) else None,
        "news":news_meta,
        "news_used_in_historical_model_features": False,
        "news_note":"Recent Upstox headlines are reported separately; they are not backfilled into historical candle rows because this feed does not establish point-in-time availability for each past candle.",
        "validation_method":"chronological expanding-window walk-forward; purged 3-bar label boundary; no shuffle",
        "cost_assumption_bps_per_side":args.cost_bps,
        "evaluation":result,
        "interpretation":"Experimental research only. Do not claim profitability or higher accuracy unless the report has valid folds and beats simple baselines out of sample."
    }
    (outdir/"model_evaluation.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    folds = result.get("folds", [])
    pd.json_normalize(folds).to_csv(outdir/"model_folds.csv", index=False)
    print(json.dumps({
        "report_path":str(outdir/"model_evaluation.json"),
        "folds_csv_path":str(outdir/"model_folds.csv"),
        "observations_received":len(candles),
        "news_status":news_meta.get("status"),
        "news_articles":news_meta.get("count"),
        "evaluation_status":result.get("status"),
        "observations_used":result.get("observations"),
        "model_comparison":result.get("model_comparison"),
        "note":result.get("note")
    }, indent=2, default=str))
    if result.get("status") not in {"ok", "evaluated"}:
        print("NOTE: A model result was not established. Collect more valid candles / verify instrument access, then rerun.")
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
