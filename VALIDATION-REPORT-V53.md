# BharatStock AI V53 — Validation Report

## Source checks
Run `python scripts/verify_v53_source.py` from the project root. The script checks the freshness UI and retained screenshot safeguards.

## Not claimed as passed
- Frontend production build: not verified in this packaging environment.
- Full browser/end-to-end visual tests: not run.
- Live Upstox token expiry/reconnect behavior: not tested with provider credentials.
- Production security review, load tests, database restore and server-side alert delivery: not verified.

## Local validation
1. In `apps/web`, run `npm install` and `npm run build`.
2. From the root, run `docker compose up -d --build` and `docker compose ps`.
3. Verify the live badge turns stale after 30 seconds without fresh updates and returns to live after new ticks arrive.
4. Test light/dark alert rows, stress P/L, no-trade backtest and missing-indicator explanations.
