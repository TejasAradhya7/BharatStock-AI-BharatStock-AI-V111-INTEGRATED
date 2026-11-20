# BharatStock AI V102 — Research Validation Upgrade

This is an additive research upgrade to V101. The existing dashboard, mobile app, API prediction route, database schema, and Upstox integration are intentionally unchanged.

## Added
- `research/V102/BharatStock_AI_V102_Model_Validation_Colab.ipynb`: Colab notebook for common chronological walk-forward comparisons, Logistic Regression, Random Forest, Extra Trees, HistGradientBoosting, optional XGBoost, NIFTY-context ablation when an index series exists, volatility-regime reporting, and optional LSTM/GRU experiments.
- Outputs: fold-level metrics, model summary, regime summary, and a JSON evidence report.

## Model completion status
The live API model is implemented (Random Forest + Extra Trees ensemble), but it is **not validated as a reliable predictive model**. The V101 audit reports 46.0% walk-forward mean accuracy versus a 53.4% fold baseline. V102 does not claim to fix this by code changes; it creates a reproducible benchmark to determine whether a better candidate exists.

Do not claim 60% accuracy unless the uploaded data produces it under this notebook's chronological protocol and it is independently reproduced. Do not deploy a research candidate to the live API solely because it wins one fold.

## Run
1. Open the notebook in Google Colab.
2. Upload the latest daily OHLCV CSV exported from BharatStock AI (columns: date/timestamp, symbol, open, high, low, close, volume).
3. Run all cells from top to bottom.
4. Download and retain all four V102 output files.
5. Share the output ZIP/CSV/JSON for a final model selection and integration audit.

## Not yet certified
This ZIP has not been fully validated on the user's Windows machine or deployment environment. Web production build, Expo build, Docker/PostgreSQL runtime, browser E2E, and live Upstox authentication remain environment-dependent. No real-money orders are placed. Educational research only; not investment advice.
