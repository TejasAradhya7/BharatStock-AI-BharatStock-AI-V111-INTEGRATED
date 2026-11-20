# BharatStock AI V94 — Multi-Stock Research

## Scope
- Requested symbols: NIFTY 50 (`^NSEI`), RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK and SBIN.
- Six models: Logistic Regression, Random Forest, Extra Trees, HistGradientBoosting, LSTM and GRU.
- Five chronological expanding-window folds on the development portion.
- Separate final 20% chronological holdout for each symbol.
- Classical final holdout metrics include accuracy, balanced accuracy, precision, recall, F1, ROC-AUC, Brier score, log loss, confusion matrix and training-only majority baseline.
- Per-symbol JSON and flattened CSV exports.

## Important limitations
- The notebook downloads data from Yahoo Finance when run in Colab; availability and history length can vary.
- Symbols with insufficient rows are marked as skipped.
- The final holdout is one historical period, not a guarantee of future performance.
- No transaction cost, slippage, tax, or execution simulation is included.
- This research notebook does not replace or deploy the live API model.

## Run
Upload `BharatStock_AI_V94_Multi_Stock_Research_Colab.ipynb` to Google Colab and choose Runtime > Run all. Download:
- `bharatstock_ai_v94_multi_stock_results.json`
- `bharatstock_ai_v94_model_comparison.csv`
