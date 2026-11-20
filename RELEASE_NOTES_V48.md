# BharatStock AI V48 — Theme & Accessibility Hardening

## Changes
- Extended light-theme surface and text rules for common quick-market, sentiment, nested panel, empty/loading state, and analysis component class names.
- Added consistent disabled-control styling.
- Improved light-theme table and Recharts grid/axis contrast.
- Standardized visible keyboard focus styling and text selection.
- Preserved existing API routes and market data providers; no synthetic demo prices added.

## Verification status
- ZIP archive integrity can be checked with `unzip -t`.
- Frontend production build and browser visual regression have NOT been run in this artifact workspace.
- Some component selectors are defensive; confirm actual class names in browser and adjust where the app uses different names.
- Do not call this release production-certified until `npm run build`, both-theme browser checks, API integration checks, and end-to-end tests pass.

## Recommended release gate
1. `cd apps/web; npm ci; npm run build`
2. From project root: `docker compose up -d --build` and `docker compose ps`
3. Verify all pages in light and dark themes at desktop and mobile widths.
4. Verify real provider timestamps, stale-data behavior, alerts, exports, and failure states.
