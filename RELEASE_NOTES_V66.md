# BharatStock AI V66 — Stock Setup Analysis and Persistent Trade Journal

## Screenshot review
- The supplied screenshots show that the candlestick chart is now rendering with provider OHLC data; the earlier blank-chart screenshot is not the current state.
- The stock heatmap from V65 remains included, with Upstox quote-backed changes and unavailable values shown as unavailable rather than invented.
- The screenshots show experimental model holdout accuracy around 53% and walk-forward results near baseline. This is weak evidence, not a reliable trading edge; no 90% accuracy claim is made.
- The screenshots show a zero-entry SMA backtest on a short sample. The dashboard continues to warn when no entries were generated. A one-month history is insufficient for a 50-session moving average, so the UI correctly shows SMA50 as unavailable until enough data is selected.

## New in V66
- Added a research setup action for the currently selected stock or index using one year of provider historical data.
- Added paired NIFTY 50 and SENSEX setup generation.
- Rules use daily close, SMA20, SMA50, RSI(14), and ATR(14). The result can be bullish watch, bearish watch, or no clear setup. It does not force a trade when conditions are not aligned.
- Stop and target levels, when a directional setup exists, are illustrative ATR multiples and not guaranteed fill prices.
- Added a SQLAlchemy `trade_ideas` table and API endpoints to create, list, and update journal status.
- Added a database-backed dashboard for saved stock/index ideas with reference close, illustrative stop/target, RSI, rationale, timestamp, and manual watching/closed/ignored statuses.
- Status labels are not broker fills; no orders or realized P/L are simulated.
- Enabled PATCH in CORS for journal status changes.

## Validation
- Python syntax compilation: PASS
- Backend tests: 84 passed
- V64 chart response contract checks: 6/6 passed
- V65 heatmap source checks: 10/10 passed
- V66 trade dashboard source checks: 11/11 passed
- Frontend production build: NOT VERIFIED because dependency installation timed out in this environment.
- Live-provider and browser regression: NOT VERIFIED in this environment; run locally after rebuilding Docker.
