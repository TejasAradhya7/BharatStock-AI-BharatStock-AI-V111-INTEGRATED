# BharatStock AI V98 — Final source-package audit

## Delivered in V98
- Preserved the existing React + TypeScript web dashboard, Expo mobile client, FastAPI backend, PostgreSQL/Docker configuration, model research code, and existing AI endpoints.
- Added a responsive AI direction assistant beside the OHLC chart.
- The panel invokes the existing `/api/predict/{symbol}` endpoint and displays UP/DOWN/INSUFFICIENT status, model score, historical holdout accuracy, and validation status.
- Explicitly labels the model as a daily next-session predictor even when the chart is displaying intraday candles.
- Retained the full AI prediction and research sections.

## Verification performed for this package
- Backend API test suite: **120 passed**, 4 deprecation warnings.
- Python source compilation: **45 files compiled**, 0 syntax errors.
- Local SQLite runtime databases, `.env` files, and Python/test caches removed from the deliverable.
- ZIP integrity is checked after packaging.

## Not verified in this environment
- Web production build: not run because `apps/web/node_modules` is not present and dependency installation/network access is not available here.
- Expo/mobile production build: not run.
- Docker/PostgreSQL deployment and browser end-to-end behavior: not run.
- Live Upstox connectivity: requires the user's private valid token and instrument permissions.
- The AI chart panel has been source-reviewed but not visually browser-tested in the target environment.

## Model accuracy — important
This release does **not** claim a new or higher model accuracy. The supplied prior validation review reports weak walk-forward results for RELIANCE.NS (44.94% mean accuracy versus a 50.63% fold-trained majority baseline). The model's confidence score is not a probability of profit. No model was silently promoted based on the displayed score. A genuine accuracy improvement requires training and comparing candidates on new chronological data, then confirming on an untouched future period.

## Run locally (Windows PowerShell)
1. Extract the ZIP.
2. Copy `.env.example` to `.env` and set a strong database password and private Upstox token. Never share `.env`.
3. Run `docker compose up --build -d` from the project root.
4. Open `http://localhost:8080` and API docs at `http://localhost:8000/docs`.
5. Run backend tests from the project root: `python -m pytest services/api/tests -q`.
6. Run web build from `apps/web`: `npm ci` then `npm run build`.
7. Verify mobile separately with `npm ci` and `npx expo config --type public` from `apps/mobile`.

Educational research software only. No real broker orders are placed.
