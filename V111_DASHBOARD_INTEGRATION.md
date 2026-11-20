# V111 dashboard integration

## What changed
- The existing V111 `walk_forward_three_class_intraday` implementation is now called by
  `GET /api/research/intraday/{symbol}` using the same fetched real Upstox candles,
  timestamp-aligned news features, fold count, and one-way cost input as the existing
  binary research benchmark.
- Its output is exposed separately at
  `evaluation.three_class_evaluation`; the original binary evaluation remains unchanged.
- The Research Lab UI now displays V111 model/baseline comparison, balanced accuracy,
  macro F1, multiclass Brier score, log loss, per-fold confusion matrices, class labels,
  target definition, and round-trip cost.
- The existing daily dashboard prediction model and its saved artifacts are not changed.
- The V111 track remains research-only and `trading_enabled` remains false.

## Validation performed on this source package
- Python compilation: `services/api/app/main.py` and `services/api/app/real_world.py` passed.
- Backend tests: `129 passed, 4 warnings`.
- Frontend TSX transpilation syntax check: zero syntax diagnostics.
- Full Vite production build was not run in this environment because dependency installation
  did not complete. The included Dockerfile performs `npm install` and `npm run build`
  during the web image build; run the Docker build commands below on the target machine.

## Rebuild on Windows PowerShell
From the folder containing `docker-compose.yml`:

```powershell
docker compose build api web
docker compose up -d --no-deps api
docker compose up -d --no-deps web
docker compose ps
```

Do not use `docker compose down -v`; the PostgreSQL and model-artifact volumes contain
persistent project data.

## How to verify
1. Open Research Lab in the dashboard.
2. Enter a valid Upstox instrument key, such as `NSE_INDEX|Nifty 50` or an equity key
   verified from the Upstox instrument master.
3. Select the candle interval and one-way cost in basis points.
4. Click **Fetch real candles & benchmark models**.
5. Confirm that both the original binary comparison and the separate
   **V111 cost-aware three-class research** section appear.

The V111 evaluation is not a live next-session prediction. Its 88.50% historical
accuracy must not be represented as evidence of predictive skill when the
majority-class baseline achieved the same accuracy.
