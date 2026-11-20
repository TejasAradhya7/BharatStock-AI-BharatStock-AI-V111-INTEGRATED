# V99 — AI model reliability upgrade

## Changes
1. Prediction requests from the dashboard now request the existing five-fold expanding-window chronological model evaluation, instead of returning an empty walk-forward block for latency.
2. API prediction output now includes descriptive RSI, moving-average gap and ATR context for the latest chart state. These are explanatory context, not causal feature attributions or trade triggers.
3. Demo trading blocks a duplicate OPEN position for the same symbol and direction. Users must close the existing position before opening another identical position.
4. Existing model candidates, baseline comparisons, chronological purging and conservative model-selection rules are preserved. No candidate is auto-promoted and no accuracy is fabricated.

## Validation expectations
The first prediction request may take longer because it runs the five chronological folds. The UI should show fold count and model comparison after the API completes. If fewer than five valid folds can be formed, the API reports the actual count and does not invent missing folds.

## Important limitations
This release does not guarantee a higher accuracy. Historical test data has already been inspected in previous project iterations and is diagnostic, not a pristine future holdout. Genuine improvement must be demonstrated on later prospective observations.
