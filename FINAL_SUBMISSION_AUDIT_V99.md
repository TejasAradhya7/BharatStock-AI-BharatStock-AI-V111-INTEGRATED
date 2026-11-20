# BharatStock AI V99 — Release verification

## Implemented
- Dashboard prediction action requests the five-fold expanding-window chronological evaluation through the prediction API.
- Existing model comparison and majority baseline are returned to the UI when evaluation has enough data.
- API includes descriptive RSI, SMA20/SMA50/EMA20 gap and ATR/close context for the latest candle.
- AI predictions page displays the current indicator context with non-causal explanatory notes.
- Demo trading prevents a second OPEN position with the same symbol and direction.
- Existing V98 chart-side AI panel, app features, model registry and API architecture are preserved.

## Tests run in this package environment
- Backend API tests: **120 passed**, 4 deprecation warnings.
- Python source compilation: **45 files, 0 syntax errors**.
- Source checks confirm the UI requests walk-forward evaluation, API accepts the query parameter, duplicate demo position guard exists, and indicator context is included.

## Not run here
- Web TypeScript/Vite production build (web dependencies are not installed in this packaging environment).
- Browser visual/end-to-end tests.
- Expo mobile build.
- Docker/PostgreSQL integration against the user's local environment.
- Live Upstox test using the user's private token.

## Model accuracy status
V99 does not claim an accuracy increase. The five-fold comparison runs the existing pre-holdout candidate evaluation and compares candidates with a fold-trained majority baseline. The existing ensemble remains the serving model; candidate results do not auto-promote a model. A genuinely improved model must win on future, previously unseen data and then be prospectively confirmed.

Educational/research use only. Not investment advice. No real broker orders are placed.
