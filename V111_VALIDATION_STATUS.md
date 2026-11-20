# V111 validation status — updated 20 November 2026

- Focused intraday research tests: **19 passed** (original recorded V111 implementation validation).
- Current grouped backend verification in this completion package: **129 passed** across five test groups; one single-process all-tests invocation exceeded the environment time limit, so tests were run in groups.
- Python source compilation check: **passed** (`python -m compileall -q services/api/app services/api/tests`).
- Real Upstox V111 experiment: **recorded** in `AI-INTRADAY-RESEARCH-V111-RESULT.json` (NIFTY 50, 5-minute candles, fetched 2026-11-19T17:41:05Z).
- Three-class result summary: `reports/evidence/V111_three_class_result_summary.json`.
- Interpretation: the 88.21% HistGradientBoosting accuracy is below the 88.50% majority baseline; balanced accuracy is 35.14%. The high raw accuracy is driven by NO_TRADE prevalence and is not directional accuracy.
- Trading remains disabled for this research evaluation.
- Daily RELIANCE.NS result on 2026-11-20: 44.94% five-fold walk-forward accuracy vs 51.26% majority baseline; status `WEAK_BELOW_BASELINE`.
- No prediction-accuracy improvement or profitability improvement is claimed.
