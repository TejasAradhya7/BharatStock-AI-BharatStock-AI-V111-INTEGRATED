# BharatStock AI research evaluation audit

## Finding
The original offline research script computed `dropna()` separately for each feature set. Because feature sets have different warm-up/missing-value requirements, their walk-forward folds could cover different dates and observations. That makes the reported feature-set comparison non-like-for-like.

## Fix in this archive
The script now builds one shared complete-case dataset across the union of all declared features and the target, then evaluates every feature set on that same population. It records the common row count and date range and rejects unsorted or duplicate date indices.

## What this does not prove
- It does not establish that any reported accuracy will generalize to future market data.
- It does not establish that the 83.45% result from the earlier run was valid.
- It does not train or integrate LSTM/GRU into the live API.
- It does not make the app suitable for automated or real-money trading.

Rerun the research script on the same CSV and compare the new results. The accuracy may change materially because the test dates are now controlled.
