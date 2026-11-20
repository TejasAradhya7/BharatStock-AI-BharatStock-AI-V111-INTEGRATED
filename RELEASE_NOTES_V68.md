# BharatStock AI V68 — Professional Chart Tools

## Added
- Switch between provider-backed candlesticks and a closing-price line chart.
- Toggle SMA 20, SMA 50, EMA 20 and Bollinger Bands directly on the price chart.
- Choose the number of visible candles (50, 100, 200 or all returned bars).
- Choose a daily chart history range (1 month, 3 months, 6 months, 1 year or 5 years).
- Keep existing intraday interval choices, OHLC hover/crosshair, volume display, theme support and beginner-friendly explanations.
- Responsive chart tool styling for light and dark themes.

## Data and limitations
- The chart continues to use provider-returned OHLC data; it does not create synthetic candles.
- Intraday history is constrained by provider availability. The daily date-range control applies to the 1D interval; weekly/monthly use the provider's longer history range, and intraday intervals use provider-compatible ranges.
- Indicators are calculated from the visible chart bars in this version. With fewer visible bars than the indicator period, the overlay begins only after sufficient bars are available.
- This is not a full TradingView Charting Library clone. Drag-to-draw trendlines, advanced order tools and broker execution are not included.
- No guarantee of trading performance or AI accuracy is made.

## Validation status
- Python API syntax checks: passed.
- Existing V63/V64 chart contract checks: passed.
- V65 heatmap and V66 trade dashboard source checks: passed.
- V68 source feature checks: passed.
- TypeScript/TSX transpile syntax check: passed.
- Full frontend production build and live browser regression: not verified; `npm install` timed out in the build environment before dependencies were installed.
