# BharatStock AI V65 — Stock Heatmap and Screenshot Audit

## Changes
- Added a stock heatmap for 15 NSE-listed stocks using the latest Upstox quote response; no synthetic prices or percentage changes are generated.
- Tiles display provider price, previous-close percentage change, positive/negative direction, and quote availability.
- Added All stocks / Gainers / Losers filters and click-through to the existing market analysis for a selected ticker.
- Added instrument mappings for ITC, Hindustan Unilever, Larsen & Toubro, Bharti Airtel, Axis Bank, Kotak Mahindra Bank, Maruti Suzuki, Sun Pharma, and Tata Motors.
- Kept index cards separate from the stock heatmap.
- Added responsive desktop/mobile layout, keyboard focus via native buttons, accessible names, and light/dark theme styles.

## Screenshot audit notes
- The supplied latest screenshots show the candlestick chart now renders OHLC bars; earlier zero-bar screenshots are no longer representative of the screenshots provided in this turn.
- The AI direction estimate is about 53% holdout accuracy and walk-forward performance is near baseline; it must be presented as weak experimental evidence, not a reliable trading edge.
- Backtest screenshots show zero generated entries and zero strategy return; the existing warning should remain visible instead of implying profitability.
- SMA(50) is correctly unavailable when only 22 observations are present.
- Heatmap values remain unavailable if Upstox does not return a quote. A valid, current Upstox token and permitted instrument access are required for new symbols.

## Validation limitations
- Python syntax, source assertions, and ZIP integrity are tested by the release script.
- A full browser regression and production frontend build must be run in the user's Docker/Windows environment; this container does not claim those checks passed.
