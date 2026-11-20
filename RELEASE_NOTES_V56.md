# BharatStock AI V56 — Prediction Validation & Trading Chart Reliability

## Changes
- Corrected the holdout majority-class baseline to derive the baseline class from the training partition only (avoids using test labels to select the baseline class).
- Added a descriptive model-confidence band to the prediction response and UI. This is not a calibrated probability of profit and does not promise 90% accuracy.
- Strengthened prediction messaging: 90% success cannot be guaranteed; assess chronological out-of-sample results across market regimes.
- Retains V55 historical chart and session-only live quote snapshot chart, theme-aware axes/tooltips, freshness status, no-trade backtest explanation, and scenario P/L display.

## Limits
- No ML model can be honestly guaranteed to achieve 90% directional accuracy on future market data. Any such claim needs rigorous out-of-sample evidence and may fail under regime changes.
- The live chart plots actual quote snapshots received while the page is open. It is not a full candle/volume chart and does not fabricate market data.
- Frontend build and runtime checks must be run in the user's environment; this package does not claim live provider or browser verification.
