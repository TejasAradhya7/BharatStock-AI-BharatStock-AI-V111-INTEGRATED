# BharatStock AI V88 — Model Evaluation Audit

## Purpose
V88 adds diagnostic metrics to model-selection evaluation. It does not automatically replace the live production model.

## Changes
- Keeps chronological expanding-window folds and the pre-holdout model-selection scope.
- Adds per-candidate mean balanced accuracy, precision for the UP class, Brier score, and log loss alongside accuracy.
- Adds explicit target-definition and metric-interpretation metadata to the walk-forward response.
- Documents that model probabilities are not calibrated probabilities of investment success and that a majority baseline is necessary context for accuracy.
- Adds regression coverage for the new metrics.

## Validation
- Focused analysis tests: `5 passed in 28.14s` in the build environment.
- The full API suite reached all test progress markers, but the runner timed out before returning a final summary; therefore a complete V88 suite pass is **not confirmed** here.
- Re-run in the user's environment from `services/api`: `python -m pytest -q`.
- Live market data and live prediction accuracy were not independently verified in this build environment.

## Interpretation
V88 is an evaluation-quality improvement, not evidence of higher predictive accuracy. Compare accuracy with the fold-trained majority baseline, consider class-aware and probability metrics, and retain an untouched future period for confirmation. No directional accuracy or investment return is guaranteed. Research only; not investment advice.
