# V81 — Model Evaluation and Backtest Fix

- Fixed the executable target alignment for intraday research (next-close entry, three-bar hold).
- Added a four-row chronological purge at walk-forward boundaries.
- Replaced overlapping/summed intraday trade-return estimates with non-overlapping, compounded strategy returns and a matched buy-and-hold benchmark.
- Added drawdown, trade count, precision, recall, F1 and ROC-AUC reporting for tree/linear and optional sequence models.
- Added a CSV evidence audit script and preserved supplied CSV evidence under `reports/evidence/`.
- Added focused regression tests for target alignment, compounding, costs, and metric output.

Validation: 99 backend tests passed; Python compile check passed; supplied holdout metrics reproduced. Live Upstox integration and the original daily backtest's exact returns remain unverified until source prices and local credentials are used.
