# V109 — Validation-selected classification decisions

## Why this change was made
The 2026-11-19 five-minute NIFTY experiment showed that the tabular classifiers predicted UP for nearly every held-out observation. Their balanced accuracy was approximately 50%, so ordinary accuracy alone concealed poor DOWN-class recognition.

## Change
- Added a separate classification decision-threshold selector.
- It evaluates a fixed threshold grid on an earlier chronological validation segment inside each walk-forward training fold.
- It selects the threshold with the best validation balanced accuracy; ties prefer the value closest to 0.50.
- If validation data is unavailable or contains only one class, the decision threshold remains 0.50.
- The selected threshold is applied to the untouched test-fold probabilities.
- The final test labels are never used to select the classification threshold.
- Trading-entry threshold selection remains separate and retains its existing cost-aware, validation-only, fail-closed behavior.
- The API response now reports the classification threshold and its validation selection diagnostics for each model/fold.

## What this does not claim
This change does not guarantee better out-of-sample accuracy, balanced accuracy, profitability, or calibrated probabilities. It may improve minority-class recognition on some folds and worsen it on others. Results must be measured on new untouched data. It does not change the underlying model probabilities or force a desired score.

## Validation performed for this source update
- `python -m py_compile app/real_world.py`: passed.
- `PYTHONPATH=. pytest -q tests/test_real_world.py`: 16 passed.
- Full API test suite was attempted twice but exceeded the available execution time; no full-suite pass is claimed here.

## Suggested next run
Run the existing intraday research endpoint again for NIFTY with the same interval and cost assumptions, then compare fold-level confusion matrices, balanced accuracy, prediction positive rate, Brier score, ROC-AUC, and cost-aware trading results. Keep the new output as a separate dated artifact; do not overwrite the prior experiment.
