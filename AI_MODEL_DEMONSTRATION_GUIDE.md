# BharatStock AI — AI model demonstration guide

## What the AI component contains

BharatStock AI has two related prediction/research paths:

1. **Daily directional prediction** (`services/api/app/analysis.py`): a persisted, versioned Random Forest + Extra Trees soft-voting ensemble. Its eight inputs are RSI, MACD/close, MACD signal/close, SMA20 gap, SMA50 gap, EMA20 gap, ATR/close, and five-session return. The target is next-session direction. The API exposes this through `/api/predict/{symbol}`.
2. **Intraday research benchmark** (`services/api/app/real_world.py`): Random Forest, HistGradientBoosting and Logistic Regression compared on real Upstox candles. It creates causal OHLCV features, predicts the executable direction from next-close entry to a three-bar holding-period exit, and compares the candidates with fold-specific majority and constant-probability baselines.

LSTM/GRU are optional research candidates. They are not represented as trained/active unless PyTorch is installed and the sequence model actually completes chronological-fold training.

## Demonstrate it in the web application

1. Start the existing stack from the project root:
   `docker compose up -d --build`
2. Open `http://localhost:8080` and navigate to the AI / Research area.
3. Enter a verified Upstox instrument key, for example `NSE_EQ|INE002A01018` for RELIANCE (verify it against your Upstox instrument master before the demo).
4. Select a 5-minute interval and an illustrative one-way cost assumption. Explain that this is a cost proxy, not a complete broker-fee schedule.
5. Select **Fetch real candles & benchmark models**.
6. Demonstrate the candle count, model comparison, fold-by-fold metrics, confusion matrices, feature list, validation method, cost assumption and disabled trading gate.
7. Use the daily prediction endpoint/UI to show the persisted model version, training row count, feature importance, validation status and the distinction between model score and verified probability of profit.

If Upstox has insufficient historical candles or is unavailable, the research endpoint must report an error/insufficient-data status. Do not substitute fabricated data. For a classroom demonstration without live credentials, use the saved research reports in `research/V103/evidence/` as historical evidence and clearly identify their run/version/date.

## Reproduce an evaluation report from real Upstox data

From the repository root, with `UPSTOX_ACCESS_TOKEN` configured in `services/api/.env`:

```powershell
python scripts/run_model_evaluation.py --instrument-key "NSE_EQ|INE002A01018" --symbol RELIANCE.NS --interval 5 --folds 3 --cost-bps 10
```

The script writes:

- `reports/model_evaluation.json` — complete run metadata, data range, fold metrics, model comparison, calibration and limitations.
- `reports/model_folds.csv` — one row per fold with model metrics for inspection in Excel.

Never paste the Upstox access token into source code, a notebook, a report, or a chat.

## How to explain the methodology

- **Features:** transformations use only current and earlier candle information.
- **Target:** after candle *t*, assume entry at close *t+1* and exit at close *t+4*. The label is the direction of that executable return.
- **Chronology:** expanding-window walk-forward folds are used; data is not shuffled.
- **Purge:** four rows are excluded at train/test boundaries to avoid overlap with the future entry/exit label.
- **Baselines:** majority class and constant training-prevalence probability are calculated from each fold's training data only.
- **Probability metrics:** Brier score and log loss measure probability error (lower is better); ECE summarizes calibration gap; ROC-AUC measures ranking ability.
- **Confusion matrix:** rows and columns are ordered DOWN, UP; matrix values are `[[TN, FP], [FN, TP]]`.
- **Trading simulation:** signals use next-close entry and non-overlapping three-bar holding windows; assumed costs are deducted. The cost proxy excludes many real-world charges, spread, impact and slippage unless included by the chosen assumption.

## Existing evidence and honest interpretation

The saved V103 multi-stock research report covers 13 stocks from 2020-12-01 through 2026-11-18 and uses five expanding chronological global-date folds. In the saved summary, the strongest displayed feature set is `stock_plus_nifty`: ExtraTrees mean accuracy 51.63%, mean balanced accuracy 51.58%, mean ROC-AUC 0.5185 and mean Brier 0.2496. HistGradientBoosting with `stock_plus_nifty` has mean accuracy 51.68%, balanced accuracy 51.55%, ROC-AUC 0.5205 and Brier 0.2505. These are modest results close to chance, not evidence of a reliable trading edge.

A saved daily NIFTY run (`nifty-ai-research-results.json`) reports model validation status `WEAK_BELOW_BASELINE`; its confidence-like score must not be described as a calibrated probability of profit. The prediction is an experimental directional estimate, not a trade instruction.

The previously reported intraday benchmark also found candidates at or below the constant-probability baseline on probability metrics, with ROC-AUC below 0.5 and no approved trading threshold. This is a valid negative research result: it shows why baseline comparison and a safety gate matter.

## What is and is not complete

Implemented: real-data ingestion, causal features, supervised labels, versioned daily model artifacts, chronological model evaluation, baseline comparisons, calibration diagnostics, cost-aware research backtest, timestamp-aware news alignment, prediction history/evaluation records, dashboard research workflow, and no-order safety gate.

Not established: a consistently profitable model, a robust out-of-sample edge across market regimes, a fully calibrated probability of profit, full historical point-in-time news coverage, or production trading authorization. Do not claim these in a viva or report.

## Short viva explanation

“BharatStock AI is a hybrid stock-analysis system. The machine-learning part uses historical market candles to engineer technical features and classify future direction. I evaluate it with chronological walk-forward validation rather than random splitting, because stock data is time-dependent. I compare Random Forest, gradient boosting and logistic regression with simple baselines, and report classification, probability-calibration and cost-aware simulation metrics. The current results are modest, so the system labels the signal as weak and keeps trading authorization disabled. This is intentional: the project demonstrates an end-to-end, leakage-aware AIML research workflow rather than claiming guaranteed returns.”
