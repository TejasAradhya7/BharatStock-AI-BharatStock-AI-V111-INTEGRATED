# BharatStock AI V76 — Workspace page navigation

## Changes
- Replaced scroll-to-anchor navigation with page-style workspace navigation.
- Added five sidebar destinations: Overview, Market analysis, AI predictions, Risk lab, and Demo trading.
- Each destination updates the URL hash and supports browser Back/Forward navigation and direct hash links.
- Added page-specific headings and responsive, horizontally scrollable mobile navigation.
- Kept market quote polling, selected ticker, analysis actions, and existing API integrations in the application; no fake live quotes were added.
- Demo trading and recent analysis history are separated from the Risk Lab.

## Page contents
- **Overview:** ticker search, watchlist, data freshness, key metrics, and price chart.
- **Market analysis:** Upstox quotes, heatmap, research journal, alerts, chart indicators, and correlation.
- **AI predictions:** direction estimate and news sentiment analysis.
- **Risk lab:** backtest, scenario stress test, historical risk metrics, and position sizing.
- **Demo trading:** virtual trade ledger and recent AI analyses.

## Validation
- ZIP archive integrity and static source checks should be run after extraction.
- Frontend production build was not run in this environment because dependencies are not installed and network package installation is unavailable. Run `npm ci` and `npm run build` in `apps/web` before relying on the release.
- Real-time market availability continues to depend on a configured backend and valid Upstox credentials; outside market hours, last-quote data may be shown.
