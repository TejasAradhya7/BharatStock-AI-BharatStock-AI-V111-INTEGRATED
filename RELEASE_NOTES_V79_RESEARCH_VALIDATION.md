# BharatStock AI V79 — Research validation upgrade

## Implemented
- Point-in-time news features are joined to intraday candle rows using `available_at <= candle timestamp`, trailing 24-hour window, and the exact Upstox instrument key.
- Chronological expanding-window evaluation with a three-bar purge between training and test windows.
- Sigmoid probability calibration using `TimeSeriesSplit` within the training fold when enough data is available.
- Held-out Brier score, log loss, expected calibration error, accuracy and balanced accuracy.
- Research-only long-entry proxy uses a configurable probability threshold (0.60) and deducts a configurable aggregate round-trip cost assumption.
- Optional LSTM/GRU sequence benchmarks train per chronological fold only when PyTorch and sufficient data are available. The scaler uses training-only statistics.
- Explicit demo-trading gate diagnostics. The intraday research endpoint never places orders or authorizes demo trades.

## Important limitations
- The cost input is an aggregate basis-point assumption, not a verified live schedule for brokerage, STT, exchange charges, GST, SEBI fees, stamp duty, spread, impact and slippage.
- The Upstox News API only supplies recent headlines; historical point-in-time news coverage is limited. Empty news features are neutral, not evidence that no news existed.
- LSTM/GRU can be skipped if PyTorch is absent or the dataset is too small. The status response reports this honestly.
- Calibration on small datasets is unstable. Demo-trading remains disabled regardless of reported scores and requires separate review and persistent outcome monitoring.
- Live Upstox, Docker/PostgreSQL, frontend production build and actual market-hours behavior must be validated in the user's own configured environment.
