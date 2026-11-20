# BharatStock AI V73 — Backtest comparison upgrade

## Changes
- Added historical comparison of SMA 5/20, 10/30, 20/50 and 50/100 rules where the selected period contains enough observations.
- Includes buy-and-hold as a benchmark.
- Each moving-average rule uses a one-observation signal delay and the same estimated one-way transaction-cost assumption as the primary backtest.
- Added comparison metrics: net return, maximum drawdown, Sharpe ratio, market exposure and trade events.
- Added a comparison table to the Strategy Risk Lab UI with an explicit warning that in-sample historical performance is not a guarantee of future results.

## Validation
- Python syntax compilation: passed.
- API tests: 84 passed.
- 14 warnings remain (pandas fillna downcasting and existing SQLAlchemy/datetime deprecation warnings).
- Web production build was not verified in this environment because `npm ci` did not finish before timeout.

## Important limitation
This upgrade does not target or promise 100% returns or accuracy. Backtest results depend on the symbol, dates, data quality, strategy and cost assumptions. It is an educational historical simulation, not investment advice. Transaction costs remain simplified and exclude brokerage, taxes, slippage, market impact and minimum charges.
