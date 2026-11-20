# V61 validation report

- Python API bytecode compilation: PASS.
- API tests: 82 passed.
- V60 source checks: 10/10 passed.
- V57 accessibility/layout/source checks: passed.
- V61 market-status/timestamp source checks: 10/10 passed.
- TypeScript/JSX transpile syntax check: PASS (0 transpile diagnostics).
- ZIP integrity: to be checked after archive creation.
- Full `npm run build`: NOT VERIFIED. `npm install` timed out and offline install could not find cached `@types/react`; dependencies were not available for a full type-check/Vite build.
- Browser regression and live Upstox/Yahoo provider checks: NOT RUN in this environment.
