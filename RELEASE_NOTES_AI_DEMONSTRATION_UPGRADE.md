# AI demonstration upgrade

## Changes
- Added confusion matrices to each tabular intraday model's out-of-sample fold metrics. Matrix order is `[[TN, FP], [FN, TP]]` with labels DOWN, UP.
- Expanded the AI research dashboard comparison to show balanced accuracy, F1, ROC-AUC, Brier score, mean fold net return, and trade count alongside the baseline models.
- Added a fold-by-fold evidence table with date range, precision, recall, calibration-related score, and confusion matrix.
- Corrected the dashboard to read `mean_fold_net_return_pct`, the field actually returned by the backend, instead of the nonexistent `sum_test_net_return_pct` field.
- Added `AI_MODEL_DEMONSTRATION_GUIDE.md` with the project model map, reproducible Upstox research command, metric explanations, existing evidence interpretation, viva script and limitations.

## Validation in the packaging environment
- `tests/test_real_world.py` and `tests/test_real_world_evaluation.py`: 22 passed.
- TSX transpile/syntax check for `apps/web/src/App.tsx`: 0 diagnostics.
- Full Vite build was not completed because `npm ci` timed out while fetching/installing dependencies in this environment. Run `npm ci` and `npm run build` in `apps/web` on the user's Windows machine before the classroom demo.
- The project user's previous full backend run reported 134 passed; the current targeted tests cover the changed backend research code.

## Research conclusion
This upgrade improves auditability and presentation; it does not claim to improve predictive accuracy. Saved V103 multi-stock evidence remains close to chance. Research results must be described honestly, and demo-trading authorization remains disabled.
