# BharatStock AI — V69 Clean Project Audit

## Changes made during this pass
- Fixed the chart's native form controls so the candle-range select, date-range select, and each indicator checkbox have an accessible `name`; the indicator checkboxes also receive unique IDs.
- Updated older source-verification scripts whose assertions referred to a previous chart implementation, so they validate the current provider-backed OHLC chart and separate live quote panel instead of removed UI.
- Removed an accidentally packaged local SQLite database and generated Python/test/TypeScript cache artifacts from the clean deliverable.
- Updated the top-level README status to match current verification and clearly disclose remaining environment-dependent checks.
- Confirmed the research paper is not part of the package.

## Verified in this environment
- Backend API tests: **84 passed**, one SQLAlchemy deprecation warning.
- Python source compilation: passed.
- All bundled `scripts/verify_*.py` source checks: passed after updating stale historical assertions.
- ZIP integrity: checked when the release archive is created.

## Not verified / blockers
- Web production build: not verified. `npm ci` was attempted, but npm registry requests failed with `EAI_AGAIN` (DNS/network unavailable).
- Expo/mobile build: not verified.
- Docker/PostgreSQL runtime: not verified because Docker is not installed in this environment.
- Live Upstox token, actual WebSocket feed, and live/historical market-provider availability: require valid credentials and network access in the target environment.
- Full browser end-to-end tests and deployed-origin CORS checks: not verified.

## Local verification steps (Windows PowerShell)
1. Copy `.env.example` to `.env`; set a strong `POSTGRES_PASSWORD` and your private `UPSTOX_ACCESS_TOKEN`. Never share the real `.env`.
2. From `workv38/`, run `docker compose up -d --build`.
3. Check `http://localhost:8000/health` and open `http://localhost:8080`.
4. In another terminal, run backend tests from `services/api`: `python -m pytest -q`.
5. From `apps/web`, run `npm ci` then `npm run build`; from `apps/mobile`, install dependencies and run `npx expo config --type public`.
6. Check browser console, API logs, database health, historical data, Upstox stream freshness, and REST fallback. Repeat when the Indian market is open to validate new ticks.

No source-only audit can honestly certify 100% completion until the remaining builds, runtime integrations, and end-to-end checks pass in the target environment.


## V69.1 — prediction model update
- Prediction training now rebuilds a soft-voting ensemble of Random Forest and Extra Trees on the latest available five-year historical dataset for each prediction request.
- Walk-forward folds use the same ensemble and chronological expanding windows; no shuffled time-series split is introduced.
- Feature importance is reported as the mean importance from the fitted tree estimators.
- UI/API messaging now clarifies that retraining happens when a prediction is requested and that the model cannot learn the outcome of a prediction before later market data makes the outcome observable.
- Backend tests rerun after the change: **84 passed** (one existing SQLAlchemy deprecation warning).
- Limitations: model accuracy is not guaranteed to improve; it must be assessed by per-symbol walk-forward results against baselines. The Upstox 403 shown in the user's screenshot is an upstream authorization/permission response and cannot be fixed without validating the configured token and account/API access. The heatmap's live coverage is limited to the instruments configured for Upstox; arbitrary NSE symbols can be searched for historical analysis, but do not imply that every ticker has a live quote mapping.
