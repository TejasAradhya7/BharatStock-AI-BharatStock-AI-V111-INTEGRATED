# BharatStock AI V101 — Correction audit

## User-reported issues reviewed
- Research Lab blank on its route.
- Old NIFTY 50/SENSEX journal cards showing price levels around 139.
- Duplicate OPEN `^NSEI` paper positions.
- Confusing AI model confidence and validation presentation.

## Implemented
- Restored Research Lab section visibility in the route-specific CSS.
- Load research provider/model status at application startup.
- Surface API-provided invalid index price quality flags in journal cards and allow marking those records ignored.
- Label the holdout majority-class baseline separately from the mean fold majority-class baseline.
- Add a cleanup action for duplicate OPEN paper positions; retain the newest position for each symbol/direction and archive older duplicates.
- Exclude archived paper positions from simulated P/L.

## Test evidence
- `python -m pytest -q` in `services/api`: 121 passed, 4 deprecation warnings.
- Python syntax compilation: 46 files, 0 errors.
- `python scripts/verify_v101_ui_fixes.py`: 6 checks passed.
- ZIP integrity checked.

## Remaining limitations
- Web build was not verified: offline npm installation failed due to a missing cached dependency (`yallist`). No claim of TypeScript/build success.
- No browser automation, Expo build, Docker/PostgreSQL test against the user's machine, or live Upstox test was performed.
- Existing database journal records and browser localStorage records are not modified merely by replacing source files. After updating, the user must click the new archive actions in the UI.
- The screenshot's 46.0% walk-forward mean accuracy versus 53.4% fold baseline remains weak evidence. The release does not change the model or claim better prediction accuracy.
- Model confidence is a model score, not a calibrated probability of profit.

## Local validation
Run from the project root:
- Backend: `cd services/api; python -m pytest -q`
- Web: `cd apps/web; npm ci; npm run build`
- Containers: `docker compose up -d --build`
- Verify `http://localhost:8000/health`, `http://localhost:8000/ready`, and the web UI at `http://localhost:8080`.

No real-money orders are placed. Educational research only; not investment advice.
