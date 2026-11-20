# BharatStock AI V101 — UI visibility and stale-record cleanup

## Changes in this release
- Fixed Research Lab navigation: the global page-hiding CSS previously hid the `#research-lab` section on the Research Lab route. The section is now explicitly shown when that route is active.
- Research status is requested on app startup so the Research Lab can display provider/model readiness without requiring a manual refresh.
- Invalid-scale NIFTY 50/SENSEX journal entries returned by the API are now visibly labelled `INVALID PRICE · DO NOT USE`; their rationale warning is displayed and the normal close/reopen action is suppressed.
- Added a user-triggered action to mark all currently loaded invalid-scale index journal entries as ignored. Records are retained for audit/history rather than silently deleted.
- Clarified that the 48.5% baseline belongs to the holdout evaluation while the 53.4% baseline belongs to the separate walk-forward folds; labels now identify each evaluation explicitly.
- Added a paper-trading cleanup action that archives duplicate OPEN positions with the same symbol and direction, retaining the newest one. Archived rows are excluded from simulated P/L.
- No broker orders, automatic trades, or model accuracy improvements are claimed.

## Verification
- Backend API test suite: 121 passed, 4 deprecation warnings.
- Python syntax compilation: 46 files checked, 0 syntax errors.
- V101 UI source regression checks: 7 passed.
- ZIP integrity: verified after packaging.

## Not verified in this environment
- Web production build / TypeScript compilation: dependencies were not available in the local npm cache; `npm ci --offline` failed because a package tarball was not cached. No online install was attempted.
- Browser end-to-end and visual tests.
- Expo/mobile build.
- Docker/PostgreSQL integration against the user's existing database.
- Live Upstox connectivity with the user's private token.

## Required after updating the local app
1. Rebuild/restart the web and API containers.
2. Open Research Lab and confirm its content renders.
3. In Market Analysis, click `Archive invalid index records` if stale invalid-scale entries appear.
4. In Demo Trading, click `Archive duplicate OPEN positions` to clean duplicates saved in this browser.
5. Run the backend test suite and check `/health`, `/ready`, live quote freshness, and browser console.

Historical model validation remains weak. This release improves UI/data-integrity handling; it does not make the model profitable or establish a reliable trading edge.

Educational research only. Not investment advice.
