# BharatStock AI V97 — Research-to-Production Reliability Upgrade

## What V97 changes

- Makes the model-artifact volume ownership deterministic at startup. A one-shot `model-artifacts-init` service initializes the named volume as UID/GID 10001 before the API starts. This addresses the root-owned named-volume issue that caused `PermissionError` in V96.
- The API image explicitly sets `BHARATSTOCK_MODEL_DIR=/app/model_artifacts` and creates the directory before switching to the non-root `appuser`.
- Keeps the existing RF + Extra Trees production predictor as the safe fallback. No experimental model is silently promoted.
- Documents and reuses existing research capabilities rather than rebuilding them: V94 multi-stock daily research; `/api/research/intraday/{symbol}` chronological intraday model comparison; time-aware news feature alignment; chronological calibration; cost-aware non-overlapping backtests; and demo-trading gate.

## Existing capabilities reused (not newly claimed)

- Classical model comparison and optional LSTM/GRU research are already present in the research code.
- The intraday research pipeline already computes accuracy, balanced accuracy, ROC-AUC, Brier score, log loss, expected calibration error, and cost-adjusted strategy metrics.
- News sentiment is aligned using `available_at` timestamps in the intraday research path. Live headline sentiment remains display-only for the daily prediction endpoint unless point-in-time training/validation is performed.
- The daily live predictor remains the versioned RF + Extra Trees ensemble. V94/V95 research candidates are not automatically deployed.

## Start and verify

From the project root:

```powershell
docker compose down
docker compose up --build -d
docker compose ps
docker compose logs --tail=80 model-artifacts-init api
```

Verify artifact permissions:

```powershell
docker compose exec api sh -lc "id; ls -ld /app/model_artifacts; test -w /app/model_artifacts && echo WRITABLE"
```

Verify prediction:

```powershell
Invoke-RestMethod "http://localhost:8000/api/predict/%5ENSEI"
```

Research endpoints:

- `GET /api/research/status` — available research methods and data requirements.
- `GET /api/research/intraday/{symbol}?instrument_key={UPSTOX_INSTRUMENT_KEY}&interval=5&cost_bps=10` — real Upstox intraday research, when token/instrument access is configured.

## Validation limits

This package does not claim improved predictive accuracy or profitability. The latest user-run NIFTY output reported 47.90% test accuracy against a 47.90% majority baseline, with 48.20% balanced accuracy and a weak signal. This is not evidence of a reliable trading edge. Fresh future-period validation and realistic costs are still required.

The `model-artifacts-init` service is designed for Docker Compose named volumes. If deploying to Kubernetes or an externally managed volume, configure equivalent ownership/permissions there.
