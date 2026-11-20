# BharatStock AI V63 — Chart Data Fix

## Fixes
- Weekly and monthly candles are aggregated from provider-supplied daily OHLCV data rather than relying on Yahoo's native weekly/monthly interval endpoints, which can return empty results intermittently.
- Candle response normalization now reads timestamp and OHLCV keys case-insensitively and accepts `time`, `datetime`, `date`, `timestamp`, or `index` as the time field.
- Invalid timestamps, incomplete OHLC values, and inconsistent high/low ranges are excluded from rendering with an explicit diagnostic instead of a blank chart with no explanation.
- No sample or fabricated candles are created. All candle prices are derived from provider-supplied data.

## Validation
- Python backend syntax compilation: passed.
- V57 accessibility/source checks: passed.
- V63 chart regression source checks: passed.
- ZIP integrity: verified after packaging.
- Live provider/browser test and full frontend production build: not verified in this environment.
