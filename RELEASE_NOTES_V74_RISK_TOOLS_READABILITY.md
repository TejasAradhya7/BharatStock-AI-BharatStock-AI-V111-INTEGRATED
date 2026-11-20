# BharatStock AI V74 — Risk Tools & Readability

## Included screenshot sections
- **Scenario stress tester:** configurable hypothetical percentage shock and share quantity; reference price, scenario price, estimated position P/L and scenario position value; input validation and a clear scenario-only disclaimer.
- **Historical risk analytics:** empirical daily VaR and CVaR at 95% and 99%, annualized volatility, downside volatility, historical maximum drawdown, calculation action and CSV export.
- **Position sizing calculator:** portfolio value, risk per trade, entry price, stop price and maximum capital allocation; quantity is constrained by both the risk budget and allocation limit.
- **Recent AI analyses:** refreshable list of saved predictions with symbol, timestamp, direction and latest close; empty/error state explains that persistence requires a working database.
- **Strategy Risk Lab:** backtest comparison table, buy-and-hold benchmark, transaction-cost input and export actions remain included from V73.

## UI/UX update
- Increased small labels and metadata text sizes across these risk tools.
- Improved line-height and wrapping for explanatory copy and assumptions.
- Increased form control heights and button readability.
- Added horizontal overflow handling for the strategy comparison table on narrow screens.
- No market values, predictions, or backtest results were fabricated or altered by the CSS update.

## Validation performed
- Backend automated tests: **84 passed**.
- 14 existing pandas/SQLAlchemy deprecation warnings remain; they did not fail the tests.
- Frontend production build not run in this environment; the archive does not include `node_modules`.

## Important limitations
- This is a research/educational analytics application, not a guarantee of profits or risk-free trading.
- Backtests are historical simulations and can be affected by data quality, look-ahead/overfitting risk, trading costs, slippage and taxes.
- Recent analysis persistence depends on the configured database being reachable.
