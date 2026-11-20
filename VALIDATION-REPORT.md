# BharatStock AI V50 — Validation Report

## Checks completed in this environment
- Backend API test suite: **82 passed** (`pytest -q` under `services/api`).
- Existing theme source checks: **8/8 passed** (`python scripts/verify_theme_source.py`).
- Source-level review confirms stress-test API formula is `scenario price × quantity - reference price × quantity` and existing tests assert a -10% shock on five shares at ₹120 produces -₹60 P/L.
- Light-theme triggered-alert row override added.
- Zero-trade backtest explanatory state added.
- Frontend P/L now derives from the prices and quantity shown, and warns if the API's P/L field disagrees.

## Not verified
- Frontend production build: **not run**. `apps/web` has no installed `node_modules`; dependency installation timed out in this environment.
- Browser end-to-end or visual regression tests: not run here.
- Live Upstox connectivity, token refresh, market-hours behavior and quote freshness: not retested here.
- Production deployment, security review, load testing, backup restoration and alert delivery: not verified.

## Recommended local validation
1. In `apps/web`, run `npm install`, then `npm run build`.
2. From project root, run `docker compose up -d --build`.
3. Check `docker compose ps` and `docker compose logs --tail=100 api web`.
4. Run a -10% scenario for 10 shares and confirm P/L equals -10% of the reference position value (before costs).
5. Trigger an alert in light mode and verify the text is readable.
6. Run a backtest with no entries and confirm the no-trades explanation appears.
7. Recheck both themes, mobile layout, market data freshness and provider disconnect recovery.
