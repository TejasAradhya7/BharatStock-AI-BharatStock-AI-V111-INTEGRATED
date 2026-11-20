# BharatStock AI V50 — Financial Calculation Audit & Reliability

Built from the V49 source. Existing app features and the Upstox integration are retained.

## Changes
- Light-theme triggered price-alert rows now use readable light colors instead of retaining a dark background.
- Stress-test P/L shown in the UI is calculated from `(scenario price - reference price) × quantity` so the displayed value agrees with the visible assumptions.
- Added a visible diagnostic if the API's `profit_loss` differs from the P/L calculated from its own reference price, scenario price and quantity. This can expose a stale API container or response mismatch.
- Backtests with zero position entries now explicitly state that no trades were generated and that zero return/drawdown is not evidence of profitability or safety.
- No demo prices or mock market-data providers were added.

## Important
This release is not a claim of production certification. Rebuild the API and web containers before checking the changes, then verify the stress calculation and alert theme in the browser. Historical and live quotes may come from different providers; show their timestamps and freshness clearly to users.
