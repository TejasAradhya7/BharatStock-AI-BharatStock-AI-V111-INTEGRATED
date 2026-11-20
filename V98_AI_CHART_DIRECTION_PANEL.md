# V98 — AI direction panel beside the price chart

## What changed
- Added a compact AI assistant panel beside the existing OHLC chart.
- The panel calls the existing `/api/predict/{symbol}` endpoint and displays UP, DOWN, or an unavailable/neutral result.
- Displays the existing model score, chronological holdout accuracy, and validation status.
- Clearly labels the predictor as a daily next-session model even when the chart is showing intraday bars.
- Links to the full AI predictions section for feature importance and detailed model information.
- Responsive layout moves the panel above the chart on narrow screens.

## Model integrity
No accuracy values were fabricated and no model was promoted based on a high in-sample score. The existing conservative RF + Extra Trees production model and its validation gates are preserved. The historical review reported weak walk-forward results for RELIANCE.NS; improving accuracy requires new out-of-sample evidence, not changing the displayed percentage.

## Verification
Source-level JSX and API contract review performed. Run the web production build, backend test suite, and live API integration in the user's environment before submission.
