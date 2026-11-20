# BharatStock AI — model evaluation and backtest audit (V81)

## Scope
This audit uses the supplied holdout prediction CSVs and the V80 Teacher Model Evidence ZIP. It focuses on the model-evaluation and intraday-backtest path. It does not certify investment performance or the entire application as production-ready.

## Evidence results reproduced
`python scripts/audit_holdout_csv_evidence.py` recomputes metrics at the fixed 0.50 classification threshold and compares them with the matching horizon row in the supplied metrics CSV. All four prediction files passed consistency checks:

| Horizon | Rows | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 1,547 | 53.33% | 54.79% | 51.20% | 52.93% | 0.5422 |
| 3 | 1,547 | 54.49% | 54.79% | 55.07% | 54.93% | 0.5497 |
| 5 | 1,546 | 49.74% | 52.25% | 34.83% | 41.80% | 0.5234 |
| 10 | 1,545 | 52.30% | 52.32% | 70.23% | 59.97% | 0.5368 |

These are recomputed from the supplied probabilities/labels; they do not independently verify the training pipeline or exclude every possible form of data leakage. The prediction files are not labelled with a model name, so they are checked against matching metric rows rather than assuming a specific model.

## Backtest evidence limitation
The supplied prediction CSVs contain `Date`, `date`, `actual`, and `prob_up`; they do **not** contain entry/exit prices, price-aligned realized returns, or a per-trade ledger. The supplied summary `bharatstock_after_cost_backtest.csv` therefore cannot be independently reproduced from the attached evidence alone. A price-aligned ledger and `bharatstock_benchmarks.csv` (or source close-price series) are needed to verify its reported returns and benchmark comparison. This release does not relabel those historical daily backtest numbers as independently verified.

## Code corrections in V81
- The intraday supervised target now matches an executable trade: signal after close *t*, enter at close *t+1*, exit at close *t+4* (three bars held). The final four rows are excluded because their entry/exit return is not yet known.
- Walk-forward boundaries purge four rows for the target's entry/exit horizon.
- Intraday evaluation uses non-overlapping three-bar candidates, a next-close entry, configurable round-trip costs, compounded strategy equity, max drawdown, and a buy-and-hold benchmark over the same candidate windows.
- Both tree/linear and optional LSTM/GRU candidates report precision, recall, F1, ROC-AUC, calibration metrics, trade count, benchmark return, and drawdown.
- Added an evidence audit script and included copies of the supplied CSVs under `reports/evidence/` for reproducibility.

## Validation performed
- CSV evidence audit: **passed** for all four prediction files; metrics matched the supplied metric table.
- Focused evaluation tests: **5 passed**.
- Full backend pytest suite: **99 passed**, with 16 existing deprecation/future warnings.
- Python compile check: **passed** for project scripts and backend Python files.

## Not yet verified
- Live Upstox retrieval and the complete real-candle walk-forward run: not executed because no private API token/instrument authorization is available in this environment.
- The original daily backtest's exact returns and benchmark: not independently reproducible without source close prices / price-aligned ledger.
- Live/historical news sentiment improving predictive performance: not established; news is not backfilled into old candles.
- Profitability, production readiness, or 100% completion: not claimed.

## Reproduce
From the repository root:

```bash
python scripts/audit_holdout_csv_evidence.py
cd services/api
pytest -q
```

For a fresh Upstox evaluation, configure `UPSTOX_ACCESS_TOKEN` in `services/api/.env` locally and use the command in `TEACHER_MODEL_AND_RESULTS_GUIDE.md`. Never put the token in source control or share it in chat.
