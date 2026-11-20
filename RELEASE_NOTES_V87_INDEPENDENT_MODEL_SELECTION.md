# BharatStock AI V87 — Independent Model-Selection Evaluation

## Purpose
V87 improves the evaluation protocol without changing the live prediction model.

## Changes
- Walk-forward model-selection folds now run only on the pre-holdout training portion; the final chronological 20% is excluded from those folds.
- Added paired moving-block bootstrap comparisons for Random Forest, Extra Trees, HistGradientBoosting, and Logistic Regression against the current RF + Extra Trees ensemble.
- Retained the existing `paired_model_comparison` response field for compatibility and added `paired_candidate_comparisons` for all candidate models.
- The API explicitly marks the final holdout as previously inspected in earlier versions, so it must be treated as diagnostic rather than a fresh confirmatory test.
- Added regression tests to verify pre-holdout model-selection scope and candidate comparison coverage.

## Validation
- API test suite: 104 passed, 4 existing deprecation warnings.
- Test command: `python -m pytest -q` (run in `services/api`; setting BLAS/OpenMP thread limits in this build environment kept execution deterministic).
- Live provider behavior and live market accuracy have not been independently verified in this build environment.

## Interpretation
V87 does not claim improved accuracy and does not switch the production model. The final holdout has already been reported in earlier project versions, so independent confirmation of any selected model requires future observations that were not used in the current comparisons. All metrics are research diagnostics, not investment advice.
