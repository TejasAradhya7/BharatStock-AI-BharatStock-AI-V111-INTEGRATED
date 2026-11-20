# V96 — AI prediction latency and 502 mitigation

- Interactive `/api/predict/{symbol}` no longer runs the full five-fold, multi-model walk-forward research suite on every click.
- Prediction response keeps the `walk_forward` fields but marks evaluation as skipped for live requests; run walk-forward evaluation in the Research Lab.
- Holdout Random Forest refit is opt-in through `predict(..., include_walk_forward=True)` and is not repeated during dashboard requests.
- Random Forest / Extra Trees use one worker to reduce CPU and memory spikes in Docker.
- Nginx API proxy read/send timeouts increased to 180 seconds for upstream market-data calls.
- Existing persisted RF + Extra Trees model and feature schema remain unchanged.
- This mitigates avoidable request load; the exact cause of the user's 502 must still be confirmed with API container logs.
