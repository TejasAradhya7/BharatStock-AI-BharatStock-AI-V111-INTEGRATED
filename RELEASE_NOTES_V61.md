# BharatStock AI V61 — Market session and timestamp fixes

## Changes
- Added an India-time regular-session indicator (usual NSE/BSE weekday session 09:15–15:30 IST). Outside those hours the interface says the market is closed/outside regular hours and explicitly notes that exchange holidays are not inferred.
- The live quote panel now labels available values as the last quote while outside regular hours, instead of implying fresh ticks are expected.
- Quote timestamps are rendered in `Asia/Kolkata` and show date and time.
- Date-only provider bars are parsed as IST calendar dates, avoiding JavaScript's UTC interpretation and potential day shifts.
- Chart axis labels use the selected candle interval, and the latest provider bar timestamp is displayed.
- Missing provider volume is displayed as `—`, not silently coerced to zero. Real provider OHLC values remain required; no sample candles are synthesized.
- Historical freshness age is computed against the India calendar date, with a note that weekends, holidays and provider delays affect interpretation.
- Added light/dark theme styles for the market-session badge.

## Limitations
- The session indicator checks weekday and regular hours, not an authoritative exchange holiday calendar. It therefore describes regular hours, not official holiday status.
- Quotes/history are still subject to provider access, delay, rate limits and data quality. No live provider request was made during this build.
