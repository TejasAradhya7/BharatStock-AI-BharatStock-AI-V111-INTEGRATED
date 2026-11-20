# BharatStock AI — AI model demonstration guide

## Where is the AI model?

The live price-direction model is in `services/api/app/analysis.py`. It fetches historical OHLCV data, constructs technical features, trains a Random Forest + Extra Trees soft-voting classifier, evaluates it chronologically, and returns a next-session UP/DOWN research signal. The live market stream is provided separately by the Upstox integration.

## What does V92 add?

V92 adds a separate research workflow rather than changing the running API. It lets you demonstrate feature ablation (original 8 vs expanded 16 predictors), compare classical ML algorithms, perform limited inner chronological model tuning, and train LSTM/GRU sequence models in Google Colab.

## Viva explanation

**Input:** historical daily Open, High, Low, Close and Volume values.

**Feature engineering:** RSI, MACD ratios, moving-average gaps, ATR ratio, returns, volatility, daily range, close location, opening gap and relative volume. Each predictor is calculated using current or previous observations only.

**Label:** `1` when the next session's close is greater than the current session's close; otherwise `0`. The latest row is excluded because its next close is not yet known.

**Models:** the running API uses a Random Forest + Extra Trees ensemble. The offline experiment compares Logistic Regression, Random Forest, Extra Trees and HistGradientBoosting; the Colab notebook also benchmarks LSTM and GRU.

**Evaluation:** chronological expanding-window folds, with a one-row purge at the train/test boundary. The baseline always predicts the majority class learned from the training fold. Report accuracy, balanced accuracy and F1; do not use a random train/test split for this time-series task.

**Limitations:** the output is a direction classification, not a price target or a profitable trading strategy. Historical metrics can be weak and can change by ticker and time period. Neural networks may not outperform simpler models. Future-period validation, realistic transaction costs and probability calibration are still required before any real-world use.
