# BharatStock AI V100 — Index Data Integrity & Model Evaluation

## Implemented from the uploaded V99 source
- Added index-price scale validation for NIFTY 50 (`^NSEI`) and SENSEX (`^BSESN`) before saving index research ideas. Implausible levels are rejected with an actionable error.
- Existing index journal entries are now annotated as `INVALID_INDEX_PRICE` when their stored reference price is outside the sanity range; the dashboard warns users not to rely on those records.
- Added walk-forward model metrics: UP recall, Matthews correlation coefficient (MCC), ROC-AUC, alongside accuracy, balanced accuracy, precision, Brier score and log loss.
- Expanded the AI prediction model-comparison display to show MCC, AUC, UP recall and Brier score per candidate.
- Added a user-triggered action to archive duplicate OPEN paper positions for the same symbol and direction, using the latest available paper price. No broker orders are placed.
- Preserved the existing dashboard, prediction model, risk lab, research journal, news sentiment and demo trading.

## Verification performed
- Backend API test suite: **121 passed**, 4 deprecation warnings.
- Python source compilation: **45 files compiled**, no syntax errors.
- Regression test added for implausible NIFTY 50 price rejection.
- ZIP integrity verified after packaging.

## Not run
- Web production build and browser end-to-end tests (web dependencies are not installed in this packaging environment).
- Expo/mobile production build.
- Docker/PostgreSQL integration against the user's machine.
- Live Upstox integration using the user's private token.
- Fresh live market-data verification.

## Accuracy status
V100 does not claim an accuracy improvement. The screenshot-provided five-fold result was 46.0% mean accuracy versus a 53.4% fold-trained majority baseline. The existing production model is not auto-promoted or replaced based on these results. Candidate selection must be confirmed on future unseen sessions and prospective tracking.

Educational research only. Not investment advice. No real broker orders are placed.
