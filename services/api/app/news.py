"""Best-effort live Yahoo Finance headline sentiment for each prediction request.

This is deliberately kept separate from the price-only predictor: recent news has
no five-year point-in-time training history, so applying it to the model output
without a properly aligned training set would create an unvalidated feature shift.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .engine import sentiment_score
from .market import validate_symbol


def _article_content(item: dict[str, Any]) -> dict[str, Any]:
    content = item.get("content")
    return content if isinstance(content, dict) else item


def _as_published(value: Any) -> str | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, str) and value.strip():
        raw = value.strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return None
            return parsed.astimezone(timezone.utc).isoformat()
        except ValueError:
            return None
    return None


def fetch_live_news_sentiment(symbol: str, limit: int = 10) -> dict[str, Any]:
    """Fetch recent ticker headlines on every call; never fail the price prediction.

    The returned aggregate is descriptive only. It is not mixed into the prediction
    probability until point-in-time historical news can be used for proper training
    and chronological out-of-sample evaluation.
    """
    normalized_symbol = validate_symbol(symbol)
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        import yfinance as yf

        raw_news = yf.Ticker(normalized_symbol).news or []
        articles: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw_news:
            if not isinstance(item, dict):
                continue
            content = _article_content(item)
            title = str(content.get("title") or content.get("headline") or "").strip()
            if not title or title.casefold() in seen:
                continue
            seen.add(title.casefold())
            provider = content.get("provider") or content.get("publisher") or {}
            if isinstance(provider, dict):
                source = str(provider.get("displayName") or provider.get("name") or "Yahoo Finance news")
            else:
                source = str(provider or "Yahoo Finance news")
            canonical = content.get("canonicalUrl") or content.get("clickThroughUrl")
            if isinstance(canonical, dict):
                url = str(canonical.get("url") or content.get("link") or "")
            else:
                url = str(canonical or content.get("link") or "")
            published = _as_published(content.get("providerPublishTime") or content.get("pubDate") or content.get("publishedAt"))
            score, label = sentiment_score(title)
            articles.append({"title": title[:500], "source": source[:160], "url": url[:2000],
                             "published_at": published, "sentiment_score": round(float(score), 4),
                             "sentiment": label})
            if len(articles) >= max(1, min(int(limit), 20)):
                break
        scores = [item["sentiment_score"] for item in articles]
        aggregate = round(sum(scores) / len(scores), 4) if scores else 0.0
        label = "Positive" if aggregate >= 0.05 else "Negative" if aggregate <= -0.05 else "Neutral"
        return {"status": "ok" if articles else "no_recent_articles", "provider": "Yahoo Finance news",
                "symbol": normalized_symbol, "fetched_at": fetched_at, "article_count": len(articles),
                "aggregate_sentiment_score": aggregate, "aggregate_sentiment": label, "articles": articles,
                "used_by_prediction_model": False,
                "note": "Fetched for this request. News sentiment is displayed separately and does not alter model probabilities until point-in-time news training and out-of-sample validation are available."}
    except Exception as exc:
        return {"status": "unavailable", "provider": "Yahoo Finance news", "symbol": normalized_symbol,
                "fetched_at": fetched_at, "article_count": 0, "aggregate_sentiment_score": None,
                "aggregate_sentiment": "Unavailable", "articles": [], "used_by_prediction_model": False,
                "note": f"News could not be fetched ({type(exc).__name__}); price-only prediction remains available."}
