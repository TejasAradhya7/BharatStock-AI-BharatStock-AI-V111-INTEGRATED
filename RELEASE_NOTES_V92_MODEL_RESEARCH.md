# V92 — AI model research upgrade

## What was added

- `services/api/scripts/model_research.py`: an offline research runner that builds the same 16 causal OHLCV features used by the V90/V91 price-model feature path, compares the original 8-feature set with the expanded 16-feature set and two interpretable subsets, and reports chronological fold metrics.
- A small nested chronological tuning step for Random Forest and HistGradientBoosting. Candidate configurations are selected only within each outer training window using three expanding inner splits; the outer test fold is not used for parameter selection.
- `BharatStock_AI_V92_Model_Research_Colab.ipynb`: a Google Colab notebook that downloads daily OHLCV, repeats the feature-ablation experiment, and trains optional LSTM and GRU sequence models with training-only scaling and chronological outer folds.

## Important boundaries

- This is an offline academic/research upgrade. It does not replace or silently alter the live API's prediction model.
- The Colab notebook's LSTM/GRU results must be run in Colab; no neural-network result is claimed in this ZIP.
- The command-line script performs classical feature ablation and nested tuning. It reports PyTorch availability but directs sequence training to the notebook.
- No feature set or model is declared a winner before the actual run. Use the majority baseline, fold variation, balanced accuracy and F1—not accuracy alone.
- The target is next-session close direction, not net trading profit. Transaction costs, slippage, taxes, market impact and execution are not modelled by this classification experiment.
- Model scores are not calibrated probabilities of investment success. This project is for academic demonstration and research, not financial advice.

## Run the offline research script

From the repository root in PowerShell:

```powershell
cd services\api
python -m pip install -r requirements.txt
python -c "import yfinance as yf; d=yf.Ticker('RELIANCE.NS').history(period='5y', auto_adjust=True); d.to_csv('RELIANCE_daily_ohlcv.csv')"
python scripts\model_research.py --csv RELIANCE_daily_ohlcv.csv --output model_research_results.json --folds 5
```

The CSV must contain Date (or Datetime) and Open, High, Low, Close, Volume columns. The JSON output includes fold-level and mean metrics for each feature set.

## Run the Colab experiment

1. Open `BharatStock_AI_V92_Model_Research_Colab.ipynb` in Google Colab.
2. Run cells from top to bottom; change `SYMBOL` if needed.
3. Enable a GPU runtime for faster LSTM/GRU training (CPU also works but may be slower).
4. Save `bharatstock_ai_research_results.json` and include it with the project submission.

## Validation performed for this package

- Research script Python compilation: passed.
- Notebook JSON parsing and Python code-cell syntax checks: passed (Colab `!pip` install magic excluded from plain-Python compilation).
- Synthetic OHLCV smoke test: feature generation and classical fold evaluation completed before nested tuning was added; after adding nested tuning, full multi-feature synthetic evaluation exceeded the execution time budget and is not claimed as passed.
- Existing application API tests were not rerun as part of this V92 research-only change. The V91 source ZIP is retained as the base; live application code is not changed by the research script or notebook.
