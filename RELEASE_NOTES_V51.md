# BharatStock AI V51 — Screenshot Follow-up Fixes

Built on V50. This is a targeted follow-up for issues visible in the supplied screenshots.

## Changes
- Keeps V50's recalculated stress-test P/L, light-theme triggered-alert styling, and no-trade backtest explanation.
- Replaces unexplained dashes for SMA (20), SMA (50), MACD and ATR with plain-language reasons when the value is unavailable.
- Keeps the existing real-data providers; no demo market prices added.

## Verification limits
- Source checks and archive integrity can be checked locally.
- Frontend production build and browser regression are not claimed unless run successfully in an environment with dependencies installed.
- Live Upstox operation depends on valid user credentials, provider access and market hours.
