# V95 — Persistent AI model integration

## What changed
- The live FastAPI prediction path now loads a versioned, per-symbol model artifact.
- If no matching artifact exists, it trains the existing Random Forest + Extra Trees soft-voting ensemble and atomically saves it.
- Artifacts are reused only when symbol, model version, exact feature schema, and labelled training-data fingerprint match. New market data invalidates the cache and triggers retraining.
- Prediction responses expose model version, artifact status, training timestamp, training row count, and feature schema.
- The existing chronological holdout and walk-forward diagnostics remain in place.

## Why V94 LSTM/GRU are not deployed
V94 is an offline research/evaluation package. It does not provide production-ready serialized models using the live API's exact eight-feature schema. Its holdout results are mixed and do not establish a universal winner. The API therefore keeps its established RF + Extra Trees production model; no research candidate is automatically promoted.

## Run
From `services/api`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Optional artifact directory:

```bash
BHARATSTOCK_MODEL_DIR=./model_artifacts
```

Default artifact directory is `services/api/model_artifacts`. It is runtime-generated and excluded from source control. Persist this directory in a Docker volume if artifacts should survive container replacement.

## Important limitations
- This is a persistent model cache, not online/continuous learning. It retrains when the labelled historical data changes.
- It uses the existing historical data provider in `fetch_history`; the Upstox feed is not silently substituted for historical training data.
- Probability output is an uncalibrated model score, not a probability of profit.
- No claim of profitability or guaranteed accuracy is made. Backtesting with costs, slippage, taxes, and future-period validation remains necessary.
