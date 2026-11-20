# V83 — Prediction Evaluation Integrity Fix

## Scope
This release is limited to prediction evaluation integrity and live-model training. It does not add dashboard features or claim a guaranteed accuracy increase.

## Changes
- Purged the final pre-test training observation in the chronological holdout split because its next-session target depends on the first test observation's close.
- Applied the same one-observation label-boundary purge to each expanding-window walk-forward fold.
- Added explicit fold metadata (`purged_boundary_observations`) and updated the evaluation method description.
- Kept holdout metrics computed before any live-model refit.
- Refit the live prediction model on all rows whose targets are observable, while the latest unlabeled row remains excluded from training.
- Added test assertions for the purge boundary.

## Validation
- API test suite: 101 passed in the packaged environment after changes.
- Four pre-existing SQLAlchemy/Python `datetime.utcnow()` deprecation warnings remain; they are unrelated to this accuracy-focused patch.
- No live market-provider benchmark was run during packaging. Out-of-sample accuracy improvement is not yet established and must be measured using fresh market data.

## Interpretation
This fix removes a one-row label-boundary leakage risk. Correcting evaluation can lower reported scores. It does not guarantee higher prediction accuracy or any specific hit rate.
