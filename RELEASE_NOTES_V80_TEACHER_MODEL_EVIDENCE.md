# V80 — Teacher model and results evidence

- Added a reproducible CLI entry point to run the existing walk-forward research engine against real Upstox intraday candles.
- Attempts the Upstox news API and reports headline count/status, including failures.
- Saves JSON model evaluation and CSV fold metrics under `reports/`.
- Added a teacher-facing guide mapping model source, evaluation method, API endpoints and report files.
- Does not include fabricated model scores or private credentials.
- Live results must be generated with the user's token and exact Upstox instrument key.
