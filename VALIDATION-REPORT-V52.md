# BharatStock AI V52 — Validation Report

## Completed in this packaging environment
- V52 source checks: **7/7 passed** (`python scripts/verify_v52_source.py`).
- Existing V50/V51 fixes remain in the source tree.
- ZIP archive integrity checked after packaging.

## Not verified
- Frontend production build: **not verified**. `npm install --no-audit --no-fund` timed out in this environment.
- Browser/end-to-end tests: not run.
- Live Upstox connectivity, token expiry and real reconnect recovery: not tested in this packaging run.
- Production security review, load testing, backup restore and alert delivery: not verified.
- The V51 validation report recorded 82 backend tests passed and 8/8 theme source checks; those historical results are not a fresh V52 test run.

## Local verification
1. In `apps/web`, run `npm install` and then `npm run build`.
2. From the project root, run `docker compose up -d --build` and `docker compose ps`.
3. Check that a quote older than 30 seconds is clearly called stale; verify that quote age recovers when fresh ticks resume.
4. Run a prediction and confirm the baseline/uncertainty note is visible.
5. Recheck light and dark theme alert rows, indicator missing-data explanations, stress test and no-trade backtest.
