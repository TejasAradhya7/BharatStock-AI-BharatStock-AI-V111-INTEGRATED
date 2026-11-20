# Teacher guide — where is the model and where are the results?

## Where the model is
- `services/api/app/real_world.py`: real-candle feature engineering, point-in-time news alignment, calibration, walk-forward model comparison, and optional LSTM/GRU research.
- `services/api/app/analysis.py`: chronological walk-forward model comparison for daily data.
- `services/api/app/main.py`: API endpoints, including `/api/research/intraday/{symbol}`, `/api/research/status`, `/api/predict/{symbol}`, and `/api/backtest/{symbol}`.
- `scripts/run_model_evaluation.py`: reproducible command that fetches real Upstox candles, attempts timestamped Upstox news, runs the evaluation, and saves a report.

## How to produce your own results
1. Install the backend dependencies from `services/api/requirements.txt`.
2. Put `UPSTOX_ACCESS_TOKEN` in `services/api/.env` (never commit/share this file).
3. Find the exact instrument key in the Upstox instrument master. Do not assume `RELIANCE.NS` is the Upstox key.
4. From the repository root run:
   `python scripts/run_model_evaluation.py --instrument-key "NSE_EQ|YOUR_REAL_INSTRUMENT_KEY" --symbol RELIANCE.NS --interval 5`
5. Open `reports/model_evaluation.json` and `reports/model_folds.csv`. These are the results to show your teacher. The script does not invent scores; if there are too few valid candles it reports insufficient data.
6. Keep a copy of the generated report with the date, instrument, data range, model comparison, and cost assumptions.

## What to show your teacher
- Model implementation: `services/api/app/real_world.py`
- Training/evaluation entry point: `scripts/run_model_evaluation.py`
- Actual output: `reports/model_evaluation.json` and `reports/model_folds.csv` after you run it with your own valid token/instrument key.
- Dashboard/API research endpoint: open the API docs at `/docs`, then inspect `/api/research/status` and `/api/research/intraday/{symbol}` with required query parameters.

## Honest limitations
- This ZIP cannot include real results generated with your private Upstox account because the token is not available here and must not be shared in chat.
- Upstox intraday history and news coverage are limited. The script uses real returned candles; it will not manufacture a long historical sample.
- News headlines without valid publication timestamps are excluded. Recent news is not a substitute for historical point-in-time news.
- Net return is an illustrative research estimate based on the configured cost assumption, not a verified broker fee schedule or a promise of profit.
- Demo trading remains gated; this research script never places orders.
