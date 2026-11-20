# BharatStock AI V52 — Production Reliability Follow-up

Built on V51. This release focuses on risk communication and market-data freshness without replacing the existing Upstox integration or adding demo prices.

## Changes
- Adds a plain-language warning when the prediction's accuracy is near the baseline or varies across validation folds.
- Adds a research-only / not-a-buy-or-sell-instruction note to the prediction result.
- Flags the last displayed live quote timestamp as stale in the live panel when it is more than 30 seconds old.
- Retains the V50/V51 stress-test calculation, light-mode alert styling, no-trade backtest explanation and missing-indicator explanations.

## Verification status
- Source-level checks and ZIP integrity are run during packaging.
- Frontend production build, browser visual regression and live Upstox reconnect behavior must be tested in an environment with dependencies and valid provider credentials. They are not claimed as passed unless explicitly recorded in the validation report.
