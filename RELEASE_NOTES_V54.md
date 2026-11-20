# BharatStock AI V54 — Screenshot Audit and Build Gate

V54 consolidates the current V50–V53 source fixes and adds a path-independent source audit script so checks work no matter which directory the script is invoked from.

## Screenshot issues represented in source
- Light-mode diagnostic/alert styling.
- Stress-test P/L displayed from scenario price minus reference price, multiplied by quantity, with mismatch warning for API values.
- Explicit no-trade backtest explanation.
- Explanations for unavailable SMA/MACD/ATR values.
- AI baseline, walk-forward uncertainty, and research-only disclaimer.
- Quote freshness state that becomes stale after 30 seconds and does not call unknown timestamps live.

## Not implemented or not proven by this release
- Server-side alert scheduling/delivery (alerts remain browser-local).
- Verified Upstox token-expiry recovery and WebSocket reconnect in a credentialed live environment.
- Successful frontend production build: npm install timed out in the packaging environment.
- Browser/end-to-end visual regression testing, production security review, load testing, and database restore test.

## Validate
From the project root run `python scripts/verify_v54_source.py`.
In `apps/web`, run `npm install` and `npm run build`.
Only after a successful build, from the project root run `docker compose up -d --build` and verify the dashboard in a browser.
