# BharatStock AI V71 — Readable UI/UX update

## Changes
- Increased typography across navigation, dashboard labels, metrics, chart tools, OHLC strip, research journal, explanations, and buttons.
- Switched the default font stack to a modern system-first Inter/Segoe UI stack so the interface remains readable even if Google Fonts cannot load.
- Improved light-theme secondary-text contrast and keyboard focus indicators.
- Added responsive font and control sizing for smaller screens.
- Preserved market data logic, indicators, API endpoints, and research journal behavior from V70.

## Validation
- ZIP archive integrity checked.
- Bundled source-verification scripts should be run locally along with a frontend production build and browser regression.
- This CSS-only update does not validate Upstox credentials or live market connectivity.
