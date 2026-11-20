from __future__ import annotations

from datetime import datetime, timezone


def test_fetch_live_news_sentiment_parses_yfinance_news(monkeypatch):
    import sys
    from types import SimpleNamespace
    from app.news import fetch_live_news_sentiment

    class FakeTicker:
        def __init__(self, symbol):
            assert symbol == "RELIANCE.NS"
            self.news = [
                {"title": "Company reports record profit growth", "publisher": "Example News",
                 "link": "https://example.com/a", "providerPublishTime": 1790000000},
                {"title": "Company faces fraud investigation", "publisher": "Example News",
                 "link": "https://example.com/b", "providerPublishTime": 1790000100},
            ]

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=FakeTicker))
    result = fetch_live_news_sentiment("RELIANCE.NS")
    assert result["status"] == "ok"
    assert result["article_count"] == 2
    assert result["articles"][0]["url"] == "https://example.com/a"
    assert result["articles"][0]["published_at"].endswith("+00:00")
    assert result["used_by_prediction_model"] is False


def test_fetch_live_news_sentiment_fails_softly(monkeypatch):
    import sys
    from types import SimpleNamespace
    from app.news import fetch_live_news_sentiment

    class FakeTicker:
        def __init__(self, symbol):
            raise RuntimeError("provider unavailable")

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=FakeTicker))
    result = fetch_live_news_sentiment("^NSEI")
    assert result["status"] == "unavailable"
    assert result["article_count"] == 0
    assert result["aggregate_sentiment_score"] is None


def test_prediction_endpoint_fetches_news_each_request(monkeypatch):
    import app.main as main_module
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main_module, "predict", lambda symbol, **kwargs: {
        "symbol": symbol.upper(), "latest_close": 100.0,
        "predicted_direction": "UP", "model": "test-model",
        "test_accuracy": 0.6, "explanation": "test result"
    })
    calls = []
    monkeypatch.setattr(main_module, "fetch_live_news_sentiment", lambda symbol: calls.append(symbol) or {
        "status": "ok", "article_count": 1, "aggregate_sentiment_score": 0.2,
        "aggregate_sentiment": "Positive", "used_by_prediction_model": False, "articles": []
    })

    class FakeSession:
        def add(self, item): pass
        def commit(self): pass
        def rollback(self): pass
        def refresh(self, item): pass
        def close(self): pass

    def override_db():
        yield FakeSession()

    main_module.app.dependency_overrides[main_module.get_db] = override_db
    try:
        with TestClient(main_module.app) as client:
            one = client.get("/api/predict/RELIANCE.NS")
            two = client.get("/api/predict/RELIANCE.NS")
        assert one.status_code == 200
        assert two.status_code == 200
        assert one.json()["news_sentiment"]["aggregate_sentiment"] == "Positive"
        assert calls == ["RELIANCE.NS", "RELIANCE.NS"]
    finally:
        main_module.app.dependency_overrides.pop(main_module.get_db, None)
