# BharatStock AI V55 — Live Chart & Backtest Diagnostics

## Changes
- Added Historical / Live intraday chart modes to the price history panel.
- Live chart records actual quote snapshots received by the browser for the selected symbol, capped at 180 points and reset when the selected symbol changes.
- Added stream/snapshot/stale status and an explicit explanation that points are session-only quote snapshots, not historical exchange candles.
- Kept historical close chart, SMA20/SMA50 overlays, CSV export, and theme-aware chart styling.
- Improved chart height and compact controls for a more trading-terminal-like chart workspace.
- Existing V54 fixes for alert styling, stress testing, unavailable indicators, zero-trade backtest messaging and AI uncertainty remain in the source.

## Important limits
- Live intraday view requires real quotes for the selected symbol and at least two received updates. It does not fabricate points.
- This is a quote-snapshot line chart, not a full candlestick/order-book terminal. Persistent tick storage, interval aggregation (1m/5m candles), volume bars, drawing tools and server-side alerts are not included.
- Backtests can legitimately produce no trades when no crossover occurs in the selected history. This release retains the explanation; strategy behavior still requires quantitative tests against multiple symbols and periods.

## Validation
- ZIP archive integrity is checked after packaging.
- Source checks cover the historical/live chart toggle, actual quote snapshot capture, stale-state messaging, no fake points, and preservation of the historical chart/export.
- Frontend production build could not be run in this packaging environment because dependency installation timed out. Run `npm install` and `npm run build` on the user's machine before deployment.
- Browser regression and live-provider reconnection testing remain pending.
