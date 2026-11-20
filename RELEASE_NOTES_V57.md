# BharatStock AI V57 — Accessibility and Layout Stability

## Screenshot-driven updates
- Added stable `id` and `name` attributes to native input, select, and textarea controls to address Chrome form-field accessibility warnings.
- Standardized minimum control heights and reserved chart/live-market/empty-state space to reduce avoidable layout movement during loading.
- Kept historical and live-snapshot chart labels distinct; live snapshots remain session-only and are not represented as exchange tick candles.
- Kept reduced-motion support.

## Important limits
- The Chrome CLS score must be measured again in the user's browser; a source patch cannot guarantee a particular CLS score across devices/network conditions.
- Current chart source data provides historical closes and live quote snapshots, not full OHLC candles. A true candlestick chart requires a reliable OHLC/intraday-candle data endpoint; V57 does not fabricate candles.
- AI performance is not promised at 90%. The displayed model score must be evaluated on fresh chronological holdout data.
