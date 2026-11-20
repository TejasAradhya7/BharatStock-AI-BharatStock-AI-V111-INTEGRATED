# BharatStock AI V49 — Theme Consistency & Chart Contrast

## Changes
- Chart grid, axes, tick labels and tooltip now use the selected theme rather than fixed dark colors.
- Light mode now explicitly styles native inputs, selects, textareas, placeholders, focus states and options.
- Light-mode chart canvas, watchlist, saved-symbol chips and empty states receive consistent surfaces and contrast.
- Reduced-motion preference is respected globally.
- Existing real provider integrations and data routes are preserved; no demo prices were added.

## Verification status
- Source-level patch checks: to be run when packaging.
- ZIP integrity: verified after packaging.
- Frontend production build and browser visual regression: not run in this environment; run `npm ci` and `npm run build` in `apps/web`, then test both themes in a browser.
- Production readiness is not certified by this source patch alone.
