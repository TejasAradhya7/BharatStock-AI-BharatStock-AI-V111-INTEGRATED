# V105 Dashboard Data-Quality and Prediction-Safety Upgrade

## Changes
- Legacy NIFTY 50 and SENSEX research-journal rows outside conservative index price sanity ranges are filtered from the normal journal API response. Existing database rows are retained for auditability; they are not deleted.
- New index research ideas continue to be rejected when provider prices are outside the configured sanity ranges.
- The chart assistant labels the model output as an uncalibrated model score, not a win probability.
- Browser demo-trade entry now requires a fresh UP/DOWN prediction, a model score of at least 60%, and validation status that is neither WEAK_BELOW_BASELINE nor INSUFFICIENT_VALIDATION. This remains a paper-only simulation and does not place broker orders.
- Existing dashboard design and core modules are preserved.

## Validation performed in this packaging session
- `python -m compileall -q services/api/app`: passed.
- `pytest -q services/api/tests/test_api.py`: 69 passed, 4 deprecation warnings.
- Full API test suite was started but exceeded the 5-minute execution window; it is not claimed as passed.
- Frontend production build was not verified: dependency installation did not complete within the available execution window. Run `npm ci && npm run build` in `apps/web` or rebuild with Docker on the target machine.
- Docker runtime, PostgreSQL persistence, live Upstox connectivity, browser E2E, Expo build and deployment are not certified by this patch.

## Notes
This upgrade does not improve or manipulate model accuracy. Historical validation remains weak for the per-symbol runtime result shown in the screenshot. A high model score is not a calibrated probability of a profitable trade.
