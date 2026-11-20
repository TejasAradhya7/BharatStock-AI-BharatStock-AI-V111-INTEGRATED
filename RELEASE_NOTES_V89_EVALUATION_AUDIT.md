# BharatStock AI V89 — Evaluation Audit

## Scope
V89 builds on the supplied V88 archive and focuses on evaluation integrity rather than changing the live prediction algorithm.

## Changes
- Validates that evaluation feature lists are non-empty and contain no duplicate names.
- Rejects missing feature/target columns and feature names containing common target/future-leakage markers (`target`, `label`, `future`, `forward`, `next_close`, `lead_`). This is a guardrail, not a proof that semantic leakage is impossible.
- Rejects target values outside binary `0/1` labels before fitting candidate models.
- Reports evaluation audit metadata: label values, feature count, common leakage-name scan, expanding windows, common test rows, one-row label-boundary purge, and train-only majority baseline.
- Reports ensemble probability metrics (UP precision, Brier score, log loss) alongside candidate models.
- Reports balanced accuracy and UP precision for the per-fold majority baseline.
- Adds regression tests for invalid labels, suspicious feature names, metric parity, and audit status.
- Keeps the production Random Forest + Extra Trees ensemble unchanged. No candidate is automatically selected from the historical folds.

## Validation
- `python -m pytest tests/test_analysis.py -q`: 7 passed in the packaging environment.
- ZIP integrity checked after packaging.
- The full API suite did not finish within the packaging environment's time limit, so a full-suite pass is not claimed here. Run `python -m pytest -q` locally.

## Important limitations
- The existing historical holdout was previously inspected and is not fresh independent confirmation.
- The evaluation's feature-name scan cannot detect all semantic leakage; feature-generation logic must also be reviewed.
- Future-period confirmation cannot be completed until new market observations arrive and the selected model is evaluated without retuning on those observations.
- Passing software tests does not establish market prediction accuracy or profitability. This is research software, not investment advice.
