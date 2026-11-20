# V84 — Live News Sentiment Per Prediction Request

## Changes
- Each `GET /api/predict/{symbol}` request attempts to fetch recent ticker news from Yahoo Finance using the existing `yfinance` dependency.
- Headlines are normalized across common Yahoo Finance response shapes and scored with the project's existing `sentiment_score` helper.
- The API response adds `news_sentiment` with provider, fetch timestamp, article count, per-headline title/source/link/publication timestamp/sentiment, and aggregate sentiment.
- News fetch failures are non-fatal: the price-only prediction still returns and `news_sentiment.status` reports `unavailable`.
- Added unit tests for response parsing, provider failures, and fetching on each prediction request.

## Important model limitation
Live sentiment is deliberately **not** mixed into the prediction probability yet. The daily price model is trained on five years of price-derived features, while the current news provider does not supply a matching five-year point-in-time archive. Adding only today's sentiment at inference would create a train/inference feature mismatch and would not be a valid accuracy improvement. Collect timestamped news going forward, align it by its true availability time, then compare price-only and price-plus-news models on identical chronological holdouts before enabling it as a model feature.

## Validation
- API test suite: 104 passed.
- Four existing SQLAlchemy/Python `datetime.utcnow()` deprecation warnings remain.
- Tests use mocked news responses; a live provider request has not been verified in this build environment.

## Usage
Call the existing endpoint as before:

`GET /api/predict/%5ENSEI`

The response now includes `news_sentiment`. This field is descriptive research information, not investment advice and not a model probability adjustment.
