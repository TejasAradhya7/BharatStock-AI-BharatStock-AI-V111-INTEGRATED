# BharatStock AI — model validation review (2026-11-04)

## Scope
This review covers the supplied source ZIP and the `RELIANCE.NS` prediction JSON supplied in the conversation. It is not a claim that the app is production-ready or that the model is profitable.

## Evidence from the supplied prediction response
- Prediction API returned `UP` for `RELIANCE.NS`; the model-reported score was 69.26%.
- Final chronological holdout accuracy was 52.10% on 238 observations, versus a training-only majority baseline of 47.06%. This holdout was previously inspected in earlier project versions and is not fresh confirmatory evidence.
- Pre-holdout expanding-window walk-forward mean accuracy for the RF + Extra Trees ensemble was 44.94%, versus a fold-trained majority baseline of 50.63%; mean balanced accuracy was 45.71%.
- Logistic Regression had 50.00% mean walk-forward accuracy and 50.62% mean balanced accuracy. This is not evidence of a reliable predictive edge; candidate comparisons did not establish a clear statistical winner.
- The reported confidence is an uncalibrated model score, not a probability of profit.
- News fetching was unavailable in the supplied response, and `used_by_prediction_model` was false.

## Changes in this review build
- Added `model_validation_status` and `walk_forward_accuracy_gap_vs_baseline` to the prediction response.
- When walk-forward accuracy and balanced accuracy are both below baseline/random-class reference levels, `signal_quality` now reports `LOW_VALIDATION_SUPPORT` instead of allowing a high model score to dominate the interpretation.
- Updated the web prediction panel to display validation status and the actual number of walk-forward folds rather than hardcoding three.
- Added a regression test for the validation-status contract.
- Removed local environment settings, SQLite runtime data, Python/pytest caches, Expo device state, and backup copies from the deliverable archive. Configuration templates remain.

## What this does not solve
These changes improve transparency and packaging hygiene; they do not magically improve predictive accuracy. Do not describe the model as 80% accurate or profitable. A future, untouched chronological period is needed for independent confirmation. News sentiment is still not an input to the main daily prediction model. Live Upstox, database/Docker, web build, and mobile build must be verified in the target environment.

## Recommended next evaluation
1. Run the API test suite and web production build on the user's Windows environment.
2. Collect predictions before outcomes are known and store prediction timestamps, probabilities, realized next-session labels, and market data provider/source.
3. Evaluate a predeclared future period without tuning against it; report accuracy, balanced accuracy, Brier score, log loss, and baseline comparisons.
4. Keep real-money order placement disabled unless a separate, documented risk/compliance review is completed.
