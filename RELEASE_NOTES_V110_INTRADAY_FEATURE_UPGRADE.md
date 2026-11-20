# BharatStock AI V110 — Intraday Feature & Model-Bias Upgrade

## Changes
- Added causal 12/24-bar returns, momentum acceleration, 24-bar volatility, 50-period SMA/EMA gaps.
- Added exchange-local time-of-day and weekday cyclical features using Asia/Kolkata timestamps.
- Added prior-close-to-current-open gap feature.
- Removed automatic class balancing from Random Forest and Logistic Regression so predicted probabilities are not deliberately shifted toward a 50/50 class prior.
- Retained chronological walk-forward folds, four-row purge, validation-only threshold selection, transaction-cost assumptions, and disabled trading gate.
- Added feature coverage assertions to tests.

## Validation
- Full backend test suite: 126 passed, 4 deprecation warnings.
- No claim is made that these changes improve out-of-sample accuracy or profitability. Re-run the same NIFTY experiment and compare against V109.
- The model must continue to be judged against fold-specific baselines using balanced accuracy, ROC-AUC, Brier score, log loss, calibration, and net return after costs.

## Important
- No accuracy target is hard-coded.
- No test labels are used for threshold selection.
- No synthetic market data is generated.
- Demo trading remains disabled.
