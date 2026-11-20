# Current AI completion snapshot — V111 (20 November 2026)

The current AI scope and measured results are documented in [`AI_MODEL_COMPLETION_AND_RESULTS_V111.md`](AI_MODEL_COMPLETION_AND_RESULTS_V111.md). **No accuracy target was forced and no model was promoted just to improve a displayed score.**

- Daily RELIANCE.NS: 44.94% five-fold walk-forward accuracy vs 51.26% fold-trained majority baseline (`WEAK_BELOW_BASELINE`).
- V111 NIFTY 50 three-class: HistGradientBoosting 88.21% raw accuracy vs 88.50% majority baseline; balanced accuracy 35.14%. NO_TRADE accounts for 88.50% of test rows, so this is not 88% directional accuracy.
- V111 experiment JSON: [`AI-INTRADAY-RESEARCH-V111-RESULT.json`](AI-INTRADAY-RESEARCH-V111-RESULT.json).
- Daily evidence snapshots: [`reports/evidence/`](reports/evidence/).
- Backend verification: 129 tests passed across grouped runs; see the completion report for the exact groups and limitations.
- Trading remains disabled for research-only V111 evaluation.

---

## V101 correction update\n\nResearch Lab visibility, invalid index journal warnings/archiving, and duplicate paper-position cleanup were corrected. See `V101_RELEASE_NOTES.md` and `FINAL_SUBMISSION_AUDIT_V101.md`. Backend tests: 121 passed; frontend build and live integrations remain unverified in this environment.\n\n# BharatStock AI — full-stack project (source review 2026-11-04)

## Current project status

This is the source package for the BharatStock AI AIML major project. It contains the React + TypeScript web dashboard, Expo mobile client, FastAPI backend, PostgreSQL/Docker configuration, technical-analysis prediction pipeline, Upstox quote/stream integration, and tests. The research paper is not included.

**Latest test evidence supplied by the project owner:** Python source compilation succeeded and `pytest services/api/tests -q` reported **114 passed**. This is the owner's reported run, not a fresh end-to-end deployment test performed during this ZIP review.

**Prediction-model status:** the API returns predictions, but the supplied `RELIANCE.NS` response shows weak pre-holdout walk-forward performance (44.94% mean accuracy versus a 50.63% fold-trained majority baseline). The 69.26% model score is uncalibrated and is not a probability of profit. The previously inspected final holdout is not fresh independent confirmation. See `MODEL_VALIDATION_REVIEW_2026-11-04.md`.

**Not verified in this review:** web production build, Expo/mobile build, Docker/PostgreSQL runtime, browser end-to-end behavior, and live Upstox/provider connectivity. Treat this as an educational research application, not a production trading system or a guarantee of profitability.

### V39 Upstox WebSocket authorization fix

- The backend requests a fresh Upstox Market Data Feed V3 `authorized_redirect_uri` for each WebSocket connection attempt instead of connecting directly to the generic feed endpoint.
- The official SDK remains responsible for protobuf decoding, subscription messages, and reconnect handling. The project overrides only the SDK feeder's connection setup.
- WebSocket TLS certificate verification is enabled; the previous SDK feeder disabled certificate verification.
- Authorization failures are reported without including the access token. Authorized URLs are not exposed through the API.
- Added regression tests for authorization URL retrieval and rejection of non-Upstox WebSocket hosts.

Validation: `services/api` test suite passes locally (82 tests). A live connection must still be verified in the user's Upstox environment after deployment; this ZIP does not claim that external live-feed verification has already succeeded.


A research-oriented Indian-market analytics app based on the supplied paper's direction: historical prices, technical indicators (RSI, MACD, SMA/EMA, ATR, volatility), a Random Forest next-session direction baseline, headline sentiment, an API, and a responsive dashboard. The project includes a React web client, Expo mobile client, FastAPI backend, and PostgreSQL logging.

> **Important:** This is an educational research build, not a production trading system. Market history is fetched through `yfinance` and can be delayed, unavailable, or subject to provider changes. Model results are experimental and do not predict or guarantee returns. No broker orders or money movement are implemented.


## Upstox live quotes (Build V11)

The dashboard can now request current Last Traded Price (LTP) snapshots from the official Upstox V3 API. The UI polls the backend every 5 seconds while open. This is **REST snapshot polling**, not a tick-by-tick WebSocket stream. Historical charts, technical indicators, model training and backtests still use the existing historical-data provider until you migrate those paths separately.

### Configure your Upstox access token

1. Copy `services/api/.env.example` to `services/api/.env` for local development, or set `UPSTOX_ACCESS_TOKEN` in the API service environment.
2. Paste your Upstox access token into `UPSTOX_ACCESS_TOKEN` locally. Do not put it in `apps/web/.env`, mobile code, Git, screenshots, or a public repository.
3. Restart FastAPI. Check `GET http://127.0.0.1:8000/api/live/status`; it should return `configured: true` without revealing the token.
4. Open the dashboard. The Upstox live market panel should refresh its quotes every 5 seconds.

For Docker Compose, put `UPSTOX_ACCESS_TOKEN=your_token` in the root `.env` file (copied from `.env.example`) before `docker compose up --build`. Keep that root `.env` private. Upstox tokens expire at 3:30 AM the following day according to the current official token documentation, so generate/update the token when needed.

### Supported default instruments

The starter mapping includes NIFTY 50, Reliance, TCS, Infosys, HDFC Bank, ICICI Bank and SBI. If an instrument is missing or your account's instrument master uses a different key, set `UPSTOX_INSTRUMENT_KEYS` to a JSON object mapping app symbols to Upstox instrument keys. For example:

```json
{"ABC.NS":{"name":"ABC Ltd","instrument_key":"NSE_EQ|YOUR_REAL_INSTRUMENT_KEY"}}
```

Use the exact key from Upstox's instrument master. Do not assume Yahoo Finance ticker strings are interchangeable with Upstox instrument keys.

### Endpoints

- `GET /api/live/status` — shows provider/configuration state without exposing credentials.
- `GET /api/live/quotes?symbols=RELIANCE.NS,TCS.NS` — fetches current Upstox V3 LTP snapshots.

The live quote route returns a clear configuration error if the token is absent and a token error if Upstox rejects it. The integration is covered by mocked API tests; a real request cannot be verified until you configure your own valid token. For true tick-by-tick streaming, the next step is a backend worker using the Upstox Market Data Feed V3 WebSocket and protobuf decoder.

Official references:
- Upstox [LTP Quotes V3](https://upstox.com/developer/api-documentation/ltp-v3/)
- Upstox [Authentication](https://upstox.com/developer/api-documentation/authentication/)
- Upstox [Market Data Feed V3](https://upstox.com/developer/api-documentation/v3/get-market-data-feed/)



## Browser-local price alerts (Build V23)

The web dashboard includes price alerts for the supported Upstox live-quote instruments. Choose a symbol, select “at or above” or “at or below”, and enter a target price. Alerts are saved in the current browser's local storage and evaluated when fresh/available quote snapshots or stream updates reach the dashboard. If browser notifications are permitted, triggered alerts also produce a desktop notification.

**Limitations:** alerts run only while the dashboard tab is open and receiving quote updates. They are not server-side alerts, do not run while the browser is closed, and do not submit trades. They cannot guarantee notification delivery.

## Project structure

- `apps/web` — React + TypeScript + Vite + Recharts dashboard
- `apps/mobile` — Expo / React Native client
- `services/api` — FastAPI endpoints, indicators, sentiment, Random Forest baseline, SQLAlchemy persistence
- `docker-compose.yml` — PostgreSQL + API services

## Run on Windows (PowerShell)

### 1. Start the API

Install Python 3.11 or 3.12 (recommended), then run:

```powershell
cd services/api
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open API docs at `http://127.0.0.1:8000/docs`. The API can start without PostgreSQL for market/sentiment endpoints, but history logging needs a working database. For the complete DB setup, use Docker Compose below.

### 2. Start the web dashboard

Open a second PowerShell window:

```powershell
cd apps/web
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:5173`. To make a production web bundle after installing dependencies, run `npm run build`; Vite writes it to `apps/web/dist`.

### 3. Start the mobile app

```powershell
cd apps/mobile
npm install
Copy-Item .env.example .env
npx expo start
```

Edit `EXPO_PUBLIC_API_URL` in `apps/mobile/.env` to your computer's LAN IP before using a physical phone. `127.0.0.1` on a phone points to the phone, not your PC. The phone and computer must be on a reachable network.

### 4. Start PostgreSQL + API with Docker

From the project root, copy `.env.example` to `.env` and change the development password before exposing services. Then run:

```powershell
docker compose up --build
```

API: `http://localhost:8000`; interactive docs: `http://localhost:8000/docs`; PostgreSQL: `localhost:5432`.

## API endpoints

- `GET /health` — API and database status
- `GET /api/market/{symbol}?period=1y` — historical market data and technical indicators
- `GET /api/predict/{symbol}` — trains/evaluates the Random Forest baseline with a chronological holdout
- `POST /api/sentiment` — scores a supplied headline
- `GET /api/history?limit=30` — recent analysis logs

Example symbols: `^NSEI`, `RELIANCE.NS`, `TCS.NS`. Provider ticker coverage can vary.

## Tests

```powershell
cd services/api
pip install -r requirements.txt
pytest -q
```

The frontend and mobile dependencies must be installed before their respective builds can be verified. Automated tests for the backend do not establish market-data uptime, predictive validity, financial performance, or production readiness.

## Current completion estimate (engineering estimate, not a test metric)

- API indicator engine and unit tests: 80%
- FastAPI routes and persistence integration: 70%
- Web dashboard source/UI: 70% (production build not verified in this environment)
- Expo mobile source/UI: 40% (Expo build not verified)
- End-to-end integration, security, and deployment: 25%
- **Overall: approximately 60%**. This estimate reflects implemented source, not verified production readiness.

Latest local checks for Build V6: **17 backend tests pass**, Python source compiles, and the ZIP archive integrity is verified. The API can load its routes and serve docs/sentiment without importing the optional yfinance provider until market data is requested. The web header checks `/health` and distinguishes online, degraded-database, and offline API states; recent AI analysis history is shown when database persistence is available. Market ticker input is validated and health responses include a UTC check timestamp. Build V6 improves database-outage behavior: a prediction can still be returned when saving its history fails (`history_saved: false`), while the history endpoint returns a clear 503 response when persistence is unavailable. Added automated tests for both failure cases. Frontend dependency installation timed out and the offline npm cache does not contain required packages, so the React production build remains unverified. Expo build, live market-provider calls, and PostgreSQL/Docker integration are also unverified.

## Before production

1. Use an authorized market-data provider and verify exchange terms.
2. Perform walk-forward evaluation, leakage checks, baselines, transaction-cost simulation, and risk reporting before publishing model claims.
3. Add authentication, rate limits, request validation, secrets management, database migrations, monitoring, and deployment hardening.
4. Restrict CORS to the deployed frontend origin.
5. Do not use this app as the sole basis for financial decisions.


## Build V8 changes

- Added a browser-local personal watchlist to the React dashboard. Users can save/remove the selected ticker, quickly reload saved tickers, and keep up to 20 entries; saved tickers remain in the current browser only (not synced between devices/accounts).
- Added automated API tests for the curated symbol list.
- Verification still required: React production build, Expo/Android build, live provider calls, and PostgreSQL/Docker integration.

## Build V9 changes

- The Random Forest prediction response now includes balanced accuracy, majority-class baseline accuracy, holdout observation count, and estimated UP-class probability where the model has enough clean data.
- Prediction explanations explicitly recommend comparing the model to the majority-class baseline; these historical metrics are not a guarantee of future results.
- The Expo mobile screen now has quick-select Indian market tickers, latest-session change, SMA20/SMA50/RSI/ATR cards, and an experimental AI analysis action showing holdout metrics.
- Added synthetic-data unit tests for prediction metric reporting and the insufficient-history branch.
- Verification: 22 API/unit tests pass, Python source compiles, and ZIP integrity is checked. React production build remains unverified because npm dependencies could not be installed in this environment; Android/Expo build, live market provider, and PostgreSQL integration remain unverified.

## Current completion estimate (V9)

- Python indicators and model evaluation output: 82%
- FastAPI endpoints and automated tests: 85%
- React web source/UI: 75% (production build unverified)
- Expo mobile source/UI: 50% (native build unverified)
- Database and live market-data integration: 45%
- Security, deployment, and end-to-end verification: 25%
- **Overall engineering estimate: approximately 66%**, not a measured production-readiness score.

## Build V10 changes

- Added `GET /api/backtest/{symbol}?period=1y`, an educational SMA20/SMA50 crossover backtest with a one-session execution lag to reduce same-close look-ahead bias.
- Reports strategy return beside buy-and-hold return, maximum strategy drawdown, annualized volatility, and a daily-return Sharpe estimate where defined.
- The endpoint explicitly lists assumptions: historical adjusted closes and no brokerage, taxes, slippage, or market impact. Results are historical illustrations, not forecasts.
- Added the Strategy Risk Lab panel to the React dashboard, including a button to run the backtest and display the comparison metrics.
- Added tests for the backtest response and insufficient-history handling.
- Verification: 24 backend tests pass and Python compilation passes. npm dependency installation failed in this environment because the npm registry could not be reached (`EAI_AGAIN`); therefore the React production build is still unverified. Expo/Android build, live market-provider calls, and PostgreSQL/Docker integration are also unverified.

## Current completion estimate (V10)

- Python indicators and model evaluation: 82%
- FastAPI API and automated tests: 87%
- React web source/UI: 78% (production build unverified)
- Expo mobile source/UI: 50% (native build unverified)
- Database and live market-data integration: 45%
- Security, deployment, and end-to-end verification: 25%
- **Overall engineering estimate: approximately 67%**. This is a rough estimate of implementation work, not a test result or production-readiness score.

## Build V11 changes — Upstox live quotes

- Added a backend-only Upstox V3 LTP integration using `UPSTOX_ACCESS_TOKEN` and optional `UPSTOX_INSTRUMENT_KEYS` configuration.
- Added `/api/live/status` and `/api/live/quotes` endpoints with input validation, timeout handling, token/rate-limit error messages and normalized quote output.
- Added a dashboard live quote panel polling the API every five seconds while open; the access token is never sent to the browser.
- Updated Docker Compose environment wiring, local environment examples and setup documentation.
- The existing historical chart and AI analysis remain historical-provider based; live quote polling is not the same as the Upstox WebSocket streaming feed.


## Build V12 — Upstox tick-by-tick WebSocket stream

V12 adds a server-side Upstox Market Data Feed V3 stream using the official `upstox-python-sdk` (protobuf decoding is handled by the SDK). FastAPI exposes `/api/live/stream` as a WebSocket that pushes new quote snapshots to connected web/mobile dashboards. The dashboards prefer the stream and fall back to REST LTP snapshots if the stream is disabled or unavailable.

### Enable streaming

In `services/api/.env`, set:

```dotenv
UPSTOX_ACCESS_TOKEN=your_current_access_token
UPSTOX_STREAM_ENABLED=true
```

Install backend dependencies from `services/api/requirements.txt` and restart the API. Docker Compose passes `UPSTOX_STREAM_ENABLED` through from the root `.env` file (defaults to `true`). Check `GET /api/live/status` for the stream connection state. The first WebSocket connection is to the local API; the status must report `connection: connected` before tick updates are considered live. Market updates depend on a valid token, instrument permissions, configured instrument keys, and market activity.

The access token must never be sent to the browser/mobile app or committed to source control. The mobile app needs network access to the backend WebSocket URL (configure `EXPO_PUBLIC_API_URL` to a reachable host, not `127.0.0.1`, when testing on a physical device). REST snapshot fallback remains available through `/api/live/quotes`.

Official reference: https://upstox.com/developer/api-documentation/v3/get-market-data-feed/

## Build V13 — reconnect resilience and stream efficiency

- The Upstox streaming worker now retries after SDK startup failures or stream disconnects with bounded exponential backoff (up to 30 seconds).
- SDK error messages are sanitized to redact the configured access token before exposing connection status.
- The dashboard WebSocket endpoint now sends updates when ticks/state change and a 15-second heartbeat, rather than polling/sending identical state four times per second per connected client.
- Web and mobile clients reconnect automatically with exponential backoff and keep REST snapshot polling active while streaming is unavailable.
- Added coverage for stream heartbeat metadata and token non-disclosure.
- These are source-level resilience improvements. A real Upstox connection still requires a valid user token and permitted instrument keys; frontend/Android production builds and live API behavior must be tested in the user's environment.

## Current completion estimate — V13

- Python AI engine and indicators: 82%
- FastAPI API and tests: 90%
- React dashboard source: 82% (production build is blocked until npm dependencies can be installed)
- Expo mobile source: 65% (Android build not verified)
- Upstox streaming integration: 78% (retry/reconnect behavior is implemented; live credentials and market ticks not verified here)
- Security, deployment and end-to-end testing: 38%
- **Overall engineering estimate: approximately 74%**. This is an estimate of implementation work, not a verified production-readiness score.

V13 backend verification: **33 tests passed**, Python compilation passed. The web build was attempted and failed because React, Recharts, Lucide and Vite-related packages are not installed in this environment; no successful frontend build is claimed. Actual Upstox tick delivery, Android/Expo build and production database/deployment still require environment-level validation.


### V14 feed freshness diagnostics

The `/api/live/status` endpoint and `/api/live/stream` packets now expose `feed_health` and `tick_age_seconds`. `feed_health` distinguishes `awaiting_first_tick`, `live`, `stale`, `unavailable`, and `unknown`; socket connectivity alone is not treated as proof that current market ticks are arriving. Configure `UPSTOX_STALE_TICK_SECONDS` (default 30, minimum 5) to adjust the freshness threshold. Outside market hours a connected socket can legitimately have stale ticks; the dashboard retains REST fallback in that case.


## Build V14 — live-feed freshness and fallback fix

- `/api/live/status` and `/api/live/stream` report `feed_health` (`awaiting_first_tick`, `live`, `stale`, `unavailable`, or `unknown`) and `tick_age_seconds`.
- A connected WebSocket with no recent ticks is no longer treated as proof of a healthy live feed. The web client keeps REST snapshot fallback active until ticks are recent.
- Configure `UPSTOX_STALE_TICK_SECONDS` to change the tick freshness threshold (default 30 seconds; minimum 5 seconds). Outside market hours, a stale feed may be normal.
- Local backend test result for V14: 35 tests passed. Python compilation passed. The React production build was attempted but could not complete because frontend packages (React, Recharts and related dependencies) are not installed in this environment; install dependencies in `apps/web` and rerun `npm run build`.


## V15 — deployment diagnostics

- `GET /health` is a liveness check and reports database state.
- `GET /ready` summarizes database connectivity, Upstox token configuration, stream connection state and feed freshness without exposing credentials.
- `UPSTOX_STREAM_REQUIRED=false` keeps readiness useful when markets are closed or streaming is optional. Set it to `true` only if a fresh tick is a deployment requirement.
- `/api/live/status` now reports REST snapshot fallback unless the stream has received a fresh tick; a connected socket alone is not reported as a live feed.

Validation: run `cd services/api && pytest -q`. A real Upstox token and market-hours connection are still required to verify live ticks end-to-end.


## V16 — full-stack Docker web deployment and SENSEX live quotes

- Added a production multi-stage Docker build for the React web dashboard and an Nginx reverse proxy for `/api`, health/readiness endpoints, and the live WebSocket route.
- Added a `web` service to Docker Compose, exposed on port `8080` by default. The API token remains in the backend environment; it is not baked into frontend assets.
- Configured Vite dev-server proxies so local web development can use same-origin API URLs without hardcoding `127.0.0.1` in the browser. The dashboard WebSocket URL now supports same-origin HTTP/HTTPS deployments.
- Added Upstox `BSE_INDEX|SENSEX` mapping and added SENSEX to the web/mobile live quote tiles.
- Added a unit test for the SENSEX mapping.

### Run the full stack

Copy the root `.env.example` to `.env`, set `UPSTOX_ACCESS_TOKEN` to your current token, then run `docker compose up --build`. The web dashboard is served at `http://localhost:8080`, API docs at `http://localhost:8000/docs`, and health at `http://localhost:8000/health`. Keep `.env` private. The first Docker build needs access to package registries.

### V16 verification caveat

Backend tests and Python compilation should be run from `services/api`. Docker web image build, Android build and a real Upstox tick still require a network-enabled environment, valid Upstox credentials, and market activity; source changes alone do not verify those runtime paths.


## Build V17 — deployment and CI hardening

- Added GitHub Actions jobs for backend tests, the React production build, and Expo config validation. This gives the repository a repeatable CI path once pushed to GitHub.
- The API Docker image now runs as a non-root user and includes a health check. Docker Compose waits for the API health check before starting the web container.
- Added Nginx security headers for content-type sniffing, clickjacking, referrer policy, and browser permissions.
- Local verification: backend tests and Python compilation should be run before release. The CI workflow has not run on GitHub from this environment; the frontend production build and Docker startup remain unverified locally because npm registry/Docker access may be unavailable.


## V18 changes — readiness and mobile feed reliability

- `/ready` now uses standard readiness semantics: it returns HTTP 200 only when the required services are ready, otherwise HTTP 503.
- Research-only deployments can be ready without an Upstox token when `UPSTOX_STREAM_REQUIRED=false`; when set to `true`, the token, enabled stream, and a fresh tick are required.
- The mobile client now mirrors the web client's freshness logic: a connected socket alone does not count as a live feed. It switches to REST snapshots until at least one fresh tick is available, and does not overwrite quote cards with stale stream snapshots.
- Added readiness regression tests for both optional and required streaming configurations.

### Readiness configuration

```dotenv
UPSTOX_STREAM_ENABLED=true
UPSTOX_STREAM_REQUIRED=false
UPSTOX_STALE_TICK_SECONDS=30
```

Use `UPSTOX_STREAM_REQUIRED=true` only if deployment should be marked unready whenever a fresh streaming tick is unavailable (including outside market hours). Keep it `false` for research endpoints or deployments that should remain usable when the market is closed.

## V19 — WebSocket capacity protection

- Added a configurable per-process cap for dashboard/mobile live-stream WebSocket connections (`MAX_LIVE_WS_CLIENTS`, default 100, clamped to 1–1000).
- Excess connections are closed with WebSocket code `1013` and a retry-later message rather than allowing unbounded clients per worker.
- `/api/live/status` reports the active client count and configured limit; stream packets include the current connected-client count.
- The connection slot is released in a `finally` block on disconnect/error.

Validation: run `cd services/api && pytest -q`. The cap is per API process, so deployment-wide limits require a shared gateway or distributed connection coordinator when running multiple workers/replicas. Actual Upstox streaming and frontend/Android builds still require environment-level verification.

## V20: upstream quota protection

V20 adds a per-process sliding-window rate limiter to endpoints that can consume
upstream quote quota or substantial compute:

- `GET /api/live/quotes`: `RATE_LIMIT_QUOTES_PER_WINDOW` (default 60)
- `GET /api/market/{symbol}`: `RATE_LIMIT_HISTORY_PER_WINDOW` (default 40)
- `GET /api/predict/{symbol}` and `GET /api/backtest/{symbol}`:
  `RATE_LIMIT_ANALYSIS_PER_WINDOW` (default 20)
- Shared window: `RATE_LIMIT_WINDOW_SECONDS` (default 60 seconds)

Limited requests receive HTTP `429`, a `Retry-After` header and a JSON retry
hint. Health, readiness, sentiment and documentation endpoints are not covered.
The limiter is per process; multi-worker/multi-replica deployments should replace
it with shared Redis-backed limiting. By default, client identity comes from the
ASGI peer address. Set `TRUST_PROXY_HEADERS=true` only when a trusted reverse
proxy overwrites `X-Forwarded-For`/`X-Real-IP`; never trust client-supplied forwarding
headers on a directly exposed API.

This is a development hardening measure, not a substitute for production auth,
centralized abuse controls, or an actual Upstox connectivity test.


## V21 update: Upstox snapshot request cache

- Identical REST quote watchlists reuse a short in-process cache to reduce duplicate upstream calls when several dashboards refresh together.
- Configure `UPSTOX_QUOTE_CACHE_SECONDS` from `0` (disabled) to `30` seconds; default is `1` second. This cache is per API process and is not a replacement for the WebSocket stream or a shared cache across replicas.
- Responses expose `cache.hit` and `cache.ttl_seconds` so clients can see when a snapshot was reused.
- This does not make cached quotes tick-by-tick or guarantee live market availability. Verify with a valid Upstox token during market hours.


## V22 — CSV export

- The historical price endpoint now has a downloadable CSV companion: `GET /api/market/{symbol}/export.csv?period=1y`.
- The web dashboard's Price history panel includes an **Export CSV** link for the currently selected ticker and period.
- The export contains historical OHLCV values and available technical indicators, with missing values left blank. It is a historical-provider export, not a live tick archive.
- Export responses use a safe filename, `Cache-Control: no-store`, and `X-Content-Type-Options: nosniff`.
- The CSV endpoint uses the existing historical-data provider and is covered by backend tests.

## V24 — Random Forest feature explainability

- The prediction response now includes sorted `feature_importance` values for RSI, MACD, MACD signal, SMA20, SMA50, EMA20, ATR and volatility.
- The web AI panel shows the five largest feature importances alongside holdout accuracy, balanced accuracy and the majority-class baseline.
- Short-history responses return an empty feature-importance list rather than implying that a model was trained.
- Feature importance describes how a fitted Random Forest used its inputs; it is not causal evidence, a guarantee, or a standalone direction signal.

Validation: run `cd services/api && pytest -q`. The React production build and live Upstox connection still require a network-enabled environment and valid credentials.


## V25 — Walk-forward model validation

V25 adds an expanding-window walk-forward evaluation to the Random Forest direction model. In addition to the existing chronological 80/20 holdout, the API trains across three chronological folds without shuffling observations or training on future rows. Each fold reports training/test observation counts, accuracy, balanced accuracy (when both classes are present), and a majority-class baseline fitted from that fold's training data. The response summarizes mean accuracy, fold-to-fold accuracy standard deviation, mean balanced accuracy, mean baseline accuracy, and the number of out-of-sample observations. The web dashboard displays these metrics alongside the existing holdout metrics and feature importances.

**Interpretation:** this is a stronger historical evaluation, not proof of predictive edge. It does not include a complete trading simulation, fees, taxes, slippage, survivorship-bias correction, or live execution validation. Do not use it as investment advice.


## V26 — Historical risk analytics

- Added `GET /api/risk/{symbol}?period=1y` for historical daily-return VaR (95%/99%), CVaR/expected shortfall (95%/99%), annualized volatility, downside volatility, and historical maximum drawdown.
- Added a Risk Analytics panel to the web dashboard.
- Added API tests for metric output, invalid periods, and insufficient history.
- Risk metrics use empirical historical returns and do not forecast or cap future losses. They exclude transaction costs, taxes, slippage, and liquidity effects.


## V27 — Position sizing calculator

Adds `GET /api/position-size` and a dashboard calculator. The calculator limits whole-share quantity by both a user-defined portfolio risk budget and maximum capital allocation. It validates long-position stop prices and reports estimated capital required and planned loss if the stop executes exactly at the entered price. It does not place orders and excludes costs, slippage, gaps and liquidity risk. This is an educational planning aid, not investment advice.

## V28 — risk-adjusted strategy diagnostics

The SMA crossover backtest now reports compounded annualized return, Sortino ratio, Calmar ratio, percentage of sessions exposed to the market, and position-entry count in addition to total return, buy-and-hold comparison, drawdown, volatility, and Sharpe ratio. These are historical descriptive metrics, not forecasts. Results exclude transaction costs, taxes, slippage, liquidity constraints, and market impact; ratios may be unstable for short samples.


## V29 — Cost-aware strategy backtesting

- The SMA crossover backtest accepts `cost_bps` (0–100, default 10) as an estimated one-way transaction cost in basis points.
- Reports gross return, net strategy return after the simplified cost estimate, estimated cumulative cost, and entry/exit turnover events.
- Dashboard includes a one-way cost input so users can compare assumptions.
- The model is intentionally simplified: it does not simulate brokerage minimums, taxes, bid/ask spread, slippage, market impact, or order execution.
- Validate with `pytest -q` from `services/api`. Frontend production build still requires installing web dependencies.


## V30 — Safe deployment diagnostics

- Added `GET /api/system/status` to report database connectivity, Python version, required-library availability, and Upstox configuration/feed status.
- The endpoint reports only whether a token is configured; it never returns the token or environment values.
- Added automated tests for diagnostic fields, dependency checks, timestamps, and credential non-disclosure.
- Use this endpoint before deployment to identify missing dependencies or unavailable integrations. A status response is a diagnostic snapshot, not a guarantee of production readiness.


## Scenario stress tester (Build V31)

The API and React dashboard include a hypothetical single-stock price-shock calculator. Enter a shock from -100% to +100% and a whole-share quantity to estimate the position's scenario price, position value and profit/loss using the latest available historical close.

- `GET /api/stress/{symbol}?shock_pct=-10&quantity=10&period=1y`
- `shock_pct` is bounded from -100 to +100; `quantity` is a non-negative whole number.
- The endpoint uses historical closing data as its reference price. It does not use a live executable quote, forecast prices, model market liquidity, or include fees, taxes, dividends and slippage.
- The result is a linear hypothetical scenario, not a forecast, stop-loss guarantee, or investment recommendation.

V31 validation: 67 backend tests passed and Python source compilation passed. The React production build was not verified because installing the frontend dependencies timed out in this environment; live Upstox data and production deployment also remain unverified.

## V32 — Backtest report export

V32 adds `GET /api/backtest/{symbol}/export.csv`, which exports the same metrics returned by the backtest JSON endpoint, including gross/net return, estimated costs, annualized metrics, drawdown, exposure, turnover, and assumptions. The React Strategy Risk Lab shows an **Export CSV** action after a successful backtest. Export responses use a sanitized filename, `Cache-Control: no-store`, and `X-Content-Type-Options: nosniff`.

Verification for V32: backend tests are run with `cd services/api && pytest -q`. Frontend production build was not verified in the build environment because `npm install` timed out; rerun `npm install` and `npm run build` in a network-enabled environment before deployment.


## V33 — Historical risk report export

- Added `GET /api/risk/{symbol}/export.csv` to export the dashboard's historical risk metrics as a downloadable one-row CSV.
- Includes empirical daily VaR/CVaR at 95% and 99%, annualized volatility, downside volatility, maximum drawdown, observation count, method, and assumptions.
- Added an **Export CSV** action to the Historical Risk Analytics panel after a successful risk calculation.
- Export uses the same risk-analysis calculation as the JSON endpoint; it does not make new predictions.


## V34 — Daily backtest equity-curve export

V34 adds `GET /api/backtest/{symbol}/equity.csv`, a downloadable daily series with close price, delayed long/flat position, daily market return, gross strategy return, estimated cost, net strategy return, gross/net strategy equity curves, buy-and-hold equity curve, and strategy drawdown. The Strategy Risk Lab exposes separate summary and daily-curve CSV downloads. The endpoint uses the same one-bar signal delay and configurable estimated one-way cost model as the existing backtest. This is a historical research tool, not an execution engine or forecast; brokerage, taxes, slippage and market impact remain excluded.

## V35 — Web dashboard error recovery

- Wrapped the React application in an error boundary so unexpected render exceptions show a recovery screen instead of a blank dashboard.
- Added **Try again** and **Reload page** actions, accessible alert semantics, and a responsive recovery layout.
- Error details are shown only in development mode; no market data or credentials are transmitted to a third-party error-reporting service.
- Verification: backend tests and Python compilation are run separately. The web production build still requires a successful npm dependency installation.


## Build V36 changes — Market data freshness

- Historical market responses now include `data_quality` metadata: returned row count, latest session date, calendar-day age, and a freshness classification.
- The React dashboard shows a freshness badge next to the historical data source, so users can distinguish recently updated history from data that may need checking.
- Freshness uses a calendar-day heuristic, not an exchange calendar. Weekends, holidays and provider delays can affect the label; it is a warning signal, not a guarantee of real-time data.
- Added tests for freshness metadata, old provider data and non-negative age calculations.
- Verification for this build is recorded in the release notes; live market data and frontend production build still require environment-specific checks.

## V38 — Frontend API timeout and connection recovery

- Routed dashboard HTTP requests through a shared `apiFetch` helper with a 15-second default timeout.
- Aborted requests now surface a clear timeout message rather than leaving the dashboard request pending indefinitely; connection failures show a backend/API URL diagnostic.
- Existing request-specific error handling and the React error boundary remain in place. WebSocket reconnection behavior is unchanged.
- Verification: backend tests and Python compilation are run separately. Frontend dependency installation timed out in this environment, so the TypeScript/Vite production build still requires verification in a network-enabled environment.


## V38 — Cross-asset correlation analysis

- Added `GET /api/analysis/correlation?symbols=^NSEI,RELIANCE.NS,TCS.NS&period=1y`.
- Calculates Pearson correlation from aligned daily close-to-close percentage returns for 2–8 distinct tickers.
- Requires at least 20 overlapping daily returns and validates ticker count, period, and provider failures.
- Added a dashboard correlation matrix with inputs for ticker symbols, observation count, and warnings about changing historical relationships.
- Added tests for symmetry/diagonal values, duplicate and invalid ticker counts, and insufficient history.

Correlation is descriptive, not causal, and is not a guarantee of future co-movement.

## V40 Trader UX improvements

- Added working in-page navigation for Overview, Market analysis, AI predictions and Risk lab.
- Added a concise first-use guide so new traders know to search a symbol, check data freshness, then review chart and risk context.
- Improved small-screen navigation, touch targets, keyboard focus visibility, reduced-motion behavior, and section scroll behavior.
- Clarified that live quote data and historical data may come from different providers, and changed the live quote badge to avoid implying a verified WebSocket connection merely because snapshots are available.
- Preserved the existing React/FastAPI/PostgreSQL architecture and existing analysis tools.

Data source note: the interface displays the configured source and freshness metadata returned by the backend. Do not treat data from different providers as identical; verify source, timestamp, and market session before relying on it. This software is an analytics tool, not a broker or a guarantee of investment outcomes.


## Build V72 — prediction research comparison

- AI Direction Estimate now reports a chronological walk-forward comparison across the RF + Extra Trees ensemble, Random Forest, Extra Trees, HistGradientBoosting, Logistic Regression, and a majority-class baseline.
- The UI shows each model's mean fold accuracy and number of evaluated folds. Scores are diagnostics, not guarantees.
- The target of 80% directional accuracy is not hard-coded or fabricated; only measured out-of-sample results are shown. Model selection and validation should be repeated across market regimes and with transaction costs before any trading use.
- Validation follows time-ordered splits because ordinary shuffled cross-validation can leak future information into training for time series.

## V77 — Real-world intraday research foundation

See `RELEASE_NOTES_V77_REAL_WORLD_HYBRID_RESEARCH.md` for the full implementation and verification boundary.

### Intraday model research

1. Configure `UPSTOX_ACCESS_TOKEN` in `services/api/.env` (never put it in frontend environment variables).
2. Start the API and open `/api/research/status` to inspect available capabilities.
3. Obtain the exact instrument key from your Upstox instrument master, then use the dashboard's **Research lab** page or call:

   `GET /api/research/intraday/RELIANCE.NS?instrument_key=NSE_EQ%7CINE...&interval=5&cost_bps=10`

   Replace `NSE_EQ|INE...` with the real instrument key. This endpoint requests real candles; it does not substitute synthetic data when access fails.
4. Fetch current Upstox headlines with `POST /api/news/upstox/sync?instrument_keys=NSE_EQ%7CINE...` (1–30 instrument keys, exact keys required). Upstox News returns only the past seven days, so it is not a historical archive. Timestamped news/event records can also be stored at `POST /api/news/events` and queried at `GET /api/news/events`. Requests must include a timezone-aware `published_at`; server `ingested_at` enforces `available_at = max(published_at, ingested_at)`.
5. The initial research endpoint compares Random Forest, HistGradientBoosting and Logistic Regression. LSTM/GRU are explicitly not represented as trained or benchmarked; those require a controlled offline training pipeline and their own walk-forward evaluation.
6. Demo trading remains disabled for this research endpoint. Do not treat raw model scores or keyword sentiment as validated trading probabilities.

Backend tests: `cd services/api && pytest -q`. A successful unit test suite does not establish live Upstox access, frontend build success, model profitability, or production readiness.

## V79 — Research calibration and sequence-model validation

V79 adds held-out calibration diagnostics (Brier score, log loss, expected calibration error), chronological sigmoid calibration where sample size allows, a configurable research-only entry threshold and cost deduction, and optional fold-wise LSTM/GRU sequence benchmarks when PyTorch and sufficient real candles are available. News features are aligned only when `available_at` is no later than the candle timestamp. The research endpoint continues to keep demo-trading authorization disabled.

See `RELEASE_NOTES_V79_RESEARCH_VALIDATION.md` for the implementation scope and remaining real-environment validation requirements. A passing test suite does not establish profitability or production readiness.


## V98 — AI direction beside the chart
A compact AI chart assistant now appears beside the OHLC chart. It uses the existing daily next-session prediction API and shows UP/DOWN, model score, holdout accuracy, and validation status. It does not promise a direction or a profitable trade. The panel is responsive and links to the full AI prediction explanation. See `V98_AI_CHART_DIRECTION_PANEL.md`.


## V98 package verification update
- Backend API suite rerun for this source package: 120 passed (4 deprecation warnings).
- Python source compilation: 45 files, no syntax errors.
- See `FINAL_SUBMISSION_AUDIT_V98.md` for environment-dependent checks that remain.


## V99 — AI model reliability upgrade
Dashboard prediction requests now run the five-fold chronological comparison, display current indicator context, and prevent duplicate open demo positions for the same symbol/direction. See `V99_AI_MODEL_RELIABILITY_UPGRADE.md`. Model accuracy remains evidence-based; no uplift is claimed without fresh out-of-sample results.


## V99 verification
- Backend API tests: 120 passed (4 deprecation warnings).
- Python source compilation: 45 files, no syntax errors.
- Web/mobile builds and live provider integration remain environment-dependent; see `FINAL_SUBMISSION_AUDIT_V99.md`.


## V100 — Index data integrity and model metrics
See `V100_RELEASE_NOTES.md` and `FINAL_SUBMISSION_AUDIT_V100.md`. The release validates index price scale, flags invalid legacy journal rows, exposes additional walk-forward metrics and provides manual duplicate paper-position archiving. It does not claim a predictive accuracy increase.
