# BharatStock AI V58 — Trading Chart and Interval Controls

## UI/UX research references
- TradingView explains that each timeframe candle represents the open, high, low and close for its interval and supports 5m, 10m, 15m, 30m, 1h/4h, daily, weekly and monthly views: https://in.tradingview.com/support/solutions/43000747934-time-intervals-how-much-market-activity-each-candle-shows/
- TradingView datafeed documentation notes that timeframe controls must be supported by the datafeed and that resolutions need real bar data: https://tradingview.com/charting-library-docs/latest/connecting_data/time-and-sessions/configure-datafeed/
- Zerodha Kite documents candle charting, interval selection, chart controls, indicators and volume/OHLC inspection: https://kite.trade/docs/kite/charting/

## Implemented
- Added an API endpoint `/api/chart/{symbol}` that returns provider OHLCV bars for 5m, 10m, 15m, 30m, 1h, 4h, 1d, 1wk and 1mo. The 10-minute and 4-hour bars are aggregated from smaller provider intervals; no sample price bars are generated.
- Added an interval toolbar and custom responsive SVG candlestick chart with bullish/bearish candle colors, high/low wicks, volume bars, price grid, time labels, hover crosshair and an OHLCV strip.
- Added provider/loading/error states, mobile toolbar styling, theme-aware colors and rate limiting for chart requests.
- Kept the existing historical close dashboard, prediction model and risk tools.

## Data and accuracy limits
- Yahoo Finance/yfinance intraday availability varies by symbol, market, and provider retention limits. The endpoint displays errors rather than fabricating missing data. The latest candle may be incomplete and prices can be delayed.
- The Upstox live quote stream remains separate from the historical OHLC chart; this revision does not claim exchange-grade tick-by-tick candles.
- No model accuracy is guaranteed. The currently reported 52.7% holdout result should be improved only through measured chronological validation, not by hard-coding a target.

## Validation status
- Python source compiles successfully.
- Source checks cover form id/name attributes, reduced-motion support, chart interval wiring and no fabricated candles.
- Frontend production build could not be completed in this environment because dependency installation timed out. Run `npm install` and `npm run build` in `apps/web`, then browser-test intervals and themes.
