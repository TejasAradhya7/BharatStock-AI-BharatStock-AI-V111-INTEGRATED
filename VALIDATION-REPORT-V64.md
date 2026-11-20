# V64 Validation Report

- Backend pytest suite: run after changes; see final validation output.
- Python compileall: run after changes; see final validation output.
- V64 chart contract source checks: run after changes; see final validation output.
- Legacy V61/V62 source checks: updated to assert actual implementation.
- ZIP integrity: run after packaging.
- Frontend production build: not verified (dependencies unavailable/timeouts in prior attempt).
- Live Yahoo Finance and browser regression: not run.
- Upstox 403: not fixed by this chart response change; valid token/permissions required.
