# BharatStock AI V86 — Robust Out-of-Sample Model Evaluation

## Changes
- Increased default expanding-window chronological evaluation from 3 to 5 folds (up to 8 supported).
- Each fold uses the same chronological test rows for the current RF + Extra Trees ensemble, standalone Random Forest, and comparison candidates.
- Retained the one-row label-boundary purge for next-session targets and trained majority-class baseline.
- Added paired per-observation correctness comparison between Random Forest and the current ensemble.
- Added a deterministic 1,000-resample moving-block bootstrap 95% interval for the paired RF-minus-ensemble accuracy difference when at least 30 paired test observations are available.
- Verdicts remain conservative: `RF_PROMISING_NOT_PROVEN`, `CURRENT_ENSEMBLE_PROMISING_NOT_PROVEN`, `NO_CLEAR_WINNER`, or `INSUFFICIENT_EVALUATION`.
- No change to the production prediction model; no claim of improved accuracy. The final chronological holdout is still reported separately and must not be repeatedly used for tuning.

## Validation
- API test suite: **104 passed**, 4 existing datetime deprecation warnings.
- Automated tests use synthetic or mocked data; this does not establish live-market accuracy.
- Live Yahoo Finance news availability remains a separate provider issue. News sentiment remains informational and is not a prediction feature.
