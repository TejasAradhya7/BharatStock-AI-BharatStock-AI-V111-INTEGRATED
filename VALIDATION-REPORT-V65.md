# V65 Validation Report

- Python syntax compilation: PASS (`python -m compileall -q services/api/app`)
- Existing backend tests: PASS (82 passed)
- V64 chart response contract: PASS (6/6)
- V65 heatmap source checks: PASS (9/9)
- ZIP archive integrity: checked at packaging time
- Frontend production build: NOT VERIFIED. `npm install --no-audit --no-fund` timed out in the build environment before dependencies finished installing.
- Live provider/browser regression: NOT VERIFIED in this environment. The heatmap uses actual quote payloads from the existing Upstox endpoint/stream and renders unavailable values as unavailable; no prices are hard-coded.

## Required local verification

From `apps/web`, run `npm install` and `npm run build`. Then from the project root run `docker compose up -d --build` and confirm that the heatmap shows provider-backed quotes for the stocks the Upstox account is authorized to access. If a stock is unavailable, check its instrument key and the Upstox response rather than replacing it with a sample value.
