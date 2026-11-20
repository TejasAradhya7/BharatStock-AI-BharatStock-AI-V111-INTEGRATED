# BharatStock AI V77 — Real-World Intraday Research Foundation

## Implemented
- Added a `news_events` persistence model with source URL, event type, headline sentiment, relevance, published time, server ingestion time and conservative `available_at`.
- Added `POST /api/news/events` and `GET /api/news/events`. Naive timestamps are rejected. A backfilled event cannot be available before server ingestion; as-of queries only return records with `available_at <= as_of`.
- Added `POST /api/news/upstox/sync` to fetch recent Upstox News API headlines for 1–30 instrument keys, persist timestamped records, and skip duplicate headlines. The provider supplies only the previous seven days of news, not a historical archive.
- Added `GET /api/research/status` to disclose which research models and dependencies are available without overstating capabilities.
- Added `GET /api/research/intraday/{symbol}` to fetch actual Upstox V3 intraday candles using an explicit Upstox instrument key and run expanding-window walk-forward comparisons for Random Forest, HistGradientBoosting and Logistic Regression.
- Added causal intraday price/volume features, a next-three-bar target, chronological folds and a simple round-trip-cost deduction for a research-only long-only proxy.
- LSTM/GRU are reported as optional/offline research candidates; they are not falsely marked as trained or benchmarked in the request path. News is stored separately and is not merged into the price model until reliable historical availability can be aligned.
- The intraday research endpoint explicitly disables demo-trading authorization. No live orders are placed and no synthetic candles are generated.

## Required setup
- Configure `UPSTOX_ACCESS_TOKEN` in `services/api/.env` and use a valid Upstox `instrument_key` (e.g. `NSE_EQ|INE...`). A Yahoo Finance ticker such as `RELIANCE.NS` is not itself an Upstox instrument key.
- Restart the API after environment changes.
- `GET /api/research/status` explains the available model families and limitations.
- `GET /api/research/intraday/RELIANCE.NS?instrument_key=NSE_EQ%7CINE...&interval=5&cost_bps=10` is an example; replace the instrument key with the verified key from your Upstox instrument master.
- Automatic Upstox News API ingestion is implemented. Other external news sources still require a separately authorized provider/connector or trusted ingestion process.

## Verification status
- Automated unit tests cover timezone rejection/normalization, sentiment bounds, causal feature calculations, ordering and insufficient-data behavior.
- Live Upstox access, credentials, news provider integration, production DB migration, web/mobile builds and LSTM/GRU training must be verified in the user's configured environment.
- This is a research foundation, not a claim of profitable predictions or a fully validated trading system.

## V78 completion pass (2026-10-30)

- Joined persisted news into the intraday research feature matrix using a strict point-in-time rule: `available_at <= candle timestamp`; only the trailing 24 hours are aggregated. The model receives event count, relevance-weighted sentiment, and mean relevance. Newly ingested/backfilled articles cannot leak into candles before ingestion.
- Research response reports whether news events were found and the exact feature/alignment policy.
- Added tests for point-in-time news alignment and neutral features when no news is available.
- Fixed a test fixture collision: the Upstox news-sync test now uses a unique article URL per run while still asserting that a repeated sync skips duplicates.

## Still not claimed as complete

- LSTM/GRU training and walk-forward benchmarking remain a separate optional research job and are not silently trained during API requests.
- No probability calibration, complete brokerage/tax/slippage model, or demo-trading authorization is introduced. The endpoint remains research-only.
- Live Upstox access, PostgreSQL/Docker runtime, and frontend build must be validated in the user's environment with their private token and configuration.
