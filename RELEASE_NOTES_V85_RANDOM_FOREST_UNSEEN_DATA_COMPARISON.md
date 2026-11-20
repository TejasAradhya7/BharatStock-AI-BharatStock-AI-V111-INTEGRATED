# BharatStock AI V85 — Random Forest vs Current Model Evaluation

## Purpose
V85 adds an explicit, reproducible comparison to determine whether a standalone Random Forest outperforms the existing Random Forest + Extra Trees soft-voting ensemble on unseen chronological data.

## What changed
- The final chronological 20% holdout is scored by both the current ensemble and a standalone Random Forest trained only on the earlier training segment.
- The response now includes `holdout_model_comparison`: both accuracies, the majority-class baseline, difference, number of unseen observations, and which model scored higher on that one holdout.
- Walk-forward evaluation now includes `paired_model_comparison`: both models are compared on the same chronological unseen folds, with fold wins/ties and mean fold accuracy difference.
- The verdict is deliberately cautious (`RF_PROMISING_NOT_PROVEN`, `CURRENT_ENSEMBLE_PROMISING_NOT_PROVEN`, `NO_CLEAR_WINNER`, or `INSUFFICIENT_FOLDS`). A small number of time folds is not presented as statistical proof.
- Added regression tests for the new metrics.

## Validation
- API test suite: **104 passed**, 4 existing deprecation warnings.
- Tests validate output structure and bounds, not real-market predictive skill. A live-market evaluation still requires running the API against actual downloaded price history.

## How to inspect
Call `/api/predict/%5ENSEI` or another supported symbol. Review:
- `holdout_model_comparison` for the one final unseen holdout.
- `walk_forward.paired_model_comparison` for same-fold repeated comparison.
- `walk_forward.model_comparison` for model-family average fold scores.

Do not switch the live model merely because Random Forest wins one holdout. Prefer it only if its gains are repeatable across chronological folds, exceed a relevant baseline, and survive further out-of-sample checks. No accuracy level is guaranteed; this is research, not investment advice.
