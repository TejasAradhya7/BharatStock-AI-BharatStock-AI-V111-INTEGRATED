# BharatStock AI V95 — Live AI artifact integration

This release connects the existing live FastAPI prediction endpoint to a persistent, versioned model artifact registry.

## Runtime behavior
1. Build the same eight causal, normalized technical features already used by the live API.
2. Keep the existing RF + Extra Trees soft-voting ensemble as the production model.
3. Load a saved artifact only when model version, symbol, feature schema, and the fingerprint of all labelled training rows match.
4. Otherwise train on available labelled rows and atomically save the new artifact.
5. Return model version, artifact status, training timestamp, training-row count and feature schema in the existing prediction JSON.

Docker Compose now mounts a named `model_artifacts` volume so trained artifacts persist when the API container is recreated.

## V94 research disposition
V94's LSTM/GRU and alternate classical models remain research candidates. The V94 package is included under `research/V94`. The research package does not provide a production artifact trained with the API's exact feature contract, and the results do not justify automatic promotion. The production model therefore remains RF + Extra Trees.

## Validation performed for this code change
- Python `compileall` passed for API app and tests.
- Focused model-registry test passed: artifact is saved, reused when the fingerprint matches, and retrained when labelled input changes.
- The full `test_analysis.py` run exceeded the 120-second execution limit in this environment; it is not reported as passing.

## Local run
From `services/api`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or with Docker Compose:

```bash
docker compose up --build -d
```

The API container stores artifacts in `/app/model_artifacts`, backed by the `model_artifacts` named volume.

## Limitations
- This is artifact persistence and data-change retraining, not online learning from each prediction.
- Training data still comes from the project's existing `fetch_history` provider. The live Upstox quote stream is not treated as historical training data.
- Model probabilities are uncalibrated scores, not probabilities of profit.
- No claim of trading profitability or guaranteed accuracy is made. Costs, slippage, taxes and genuinely future holdout validation remain necessary.
