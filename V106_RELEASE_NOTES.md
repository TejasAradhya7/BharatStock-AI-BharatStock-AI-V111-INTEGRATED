# BharatStock AI V106 — Dashboard Data Clarity Fix

This release builds on V105 and preserves the existing application structure.

## Changes
- OHLC chart volume now displays an em dash when the selected candle's provider volume is null, non-finite, zero, or negative. This avoids presenting an unavailable/zero placeholder as a measured volume value.
- Historical source metadata is split into responsive, wrapping elements so the provider/source text and freshness badge do not collide at common viewport widths.
- Historical observation metadata explicitly says the latest daily bar may be provisional; it is not represented as a confirmed completed exchange-session close.
- AI prediction panel explains that holdout and walk-forward accuracy use different evaluation procedures/sample windows and recommends comparing each against its own baseline.

## Validation
- Source-level patch checks completed.
- ZIP integrity checked after packaging.
- Frontend production build was not run in this environment because `apps/web/node_modules` is absent. Run `npm ci && npm run build` in `apps/web` or use Docker Compose to verify the production build.
- No new model training or accuracy changes were made. Existing validation figures are preserved.
