# BharatStock AI — AI Research Upgrade (2026-11-06)

## What changed

This upgrade improves the intraday research/evaluation path without changing the daily prediction endpoint, database schema, Upstox authentication, news ingestion policy, or frontend.

### Causal features added
`build_intraday_features` now also calculates:
- `ema_gap_8` and `ema_gap_21`: close relative to causal exponential moving averages.
- `body_pct`: candle body divided by close.
- `close_location`: close's location within the candle's high-low range, clipped to [0, 1].

These features use only the current and earlier OHLC values. They do not use future candles. The executable target remains unchanged: signal at close[t], entry at close[t+1], exit at close[t+4].

### Fold-specific baselines
Each chronological test fold now reports:
- `Majority-class baseline`
- `Constant-probability baseline`

Both are estimated from that fold's training labels only. The test fold is not used to construct the baseline. The result includes train/test positive rates, test class counts, prediction positive rates, and predicted class counts for tabular models.

The model comparison now includes the baseline rows, so model performance can be assessed against simple references rather than accuracy in isolation.

### Safety
- The four-row purge remains in place.
- Threshold selection remains validation-only and fail-closed.
- The research endpoint does not enable trading or place orders.
- No synthetic market candles are generated.
- No target, probability, or accuracy values are altered to make results look better.

## Run in Docker (PowerShell)

From the project root:

```powershell
docker compose build api
docker compose up -d api
docker compose exec api python -m pytest -q tests
```

Then rerun the real-data NIFTY research endpoint:

```powershell
Invoke-RestMethod "http://localhost:8000/api/research/intraday/%5ENSEI?instrument_key=NSE_INDEX%7CNifty%2050" |
    ConvertTo-Json -Depth 30 |
    Out-File -Encoding utf8 .\nifty_research_upgraded.json
```

Inspect:
- `evaluation.feature_columns` for the added features.
- `evaluation.folds[].class_diagnostics` for train/test class balance.
- `evaluation.folds[].Majority-class baseline` and `Constant-probability baseline`.
- `evaluation.model_comparison` for baseline-versus-model comparisons.

## How to judge success

Do not use accuracy alone. Compare each model with both baselines on the same chronological folds:
- Balanced accuracy and ROC-AUC for discrimination.
- Brier score and log loss for probability quality (lower is better).
- ECE for calibration, interpreted cautiously on small test folds.
- Net returns after realistic costs only when a threshold has been selected on prior validation data and the test fold has actual trades.

A result is not a validated edge merely because one fold or one metric improves. Repeat on multiple instruments and a longer period, preserve untouched future data, and include realistic Indian transaction costs, spread and slippage. Keep `INSUFFICIENT_VALIDATION` and demo trading disabled unless the evidence justifies a change.

## Not claimed as complete
This patch does not claim that the model has achieved a profitable edge. LSTM/GRU are still optional candidates and remain skipped in the API environment unless PyTorch is installed and the sequence-model conditions are met. News features remain limited by the point-in-time news records actually stored for the instrument.
