from fastapi.testclient import TestClient
from app.main import app


def test_root_and_docs_are_available():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["name"] == "BharatStock AI API"
        assert client.get("/openapi.json").status_code == 200


def test_sentiment_endpoint_validates_and_scores_text():
    with TestClient(app) as client:
        response = client.post("/api/sentiment", json={"text": "Company reports strong growth and record profit"})
        assert response.status_code == 200
        assert response.json()["label"] == "Positive"
        assert response.json()["score"] > 0


def test_sentiment_rejects_empty_text():
    with TestClient(app) as client:
        response = client.post("/api/sentiment", json={"text": ""})
        assert response.status_code == 422


def test_market_period_is_validated_before_provider_call():
    with TestClient(app) as client:
        response = client.get("/api/market/RELIANCE.NS?period=banana")
        assert response.status_code == 422


def test_health_endpoint_reports_api_and_database_state():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in {"ok", "degraded"}
        assert response.json()["database"] in {"connected", "unavailable"}


def test_market_rejects_malformed_ticker_without_provider_call():
    with TestClient(app) as client:
        response = client.get("/api/market/%20%20")
        assert response.status_code == 422


def test_market_endpoint_serializes_indicator_history(monkeypatch):
    import pandas as pd
    import app.main as main_module

    index = pd.to_datetime(["2026-10-12", "2026-10-13"])
    fake = pd.DataFrame({
        "Open": [100.0, 101.0], "High": [103.0, 104.0],
        "Low": [99.0, 100.0], "Close": [102.0, 103.0],
        "Volume": [1000, 1200], "RSI": [50.0, 55.0],
        "SMA20": [101.0, 101.5], "SMA50": [99.0, 99.5],
    }, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: fake)
    with TestClient(app) as client:
        response = client.get("/api/market/RELIANCE.NS?period=1mo")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "RELIANCE.NS"
    assert len(payload["rows"]) == 2
    assert payload["rows"][-1]["Close"] == 103.0
    assert payload["data_quality"]["rows_returned"] == 2
    assert payload["data_quality"]["latest_session_date"] == "2026-10-13"
    assert payload["data_quality"]["freshness"] in {"recent", "check_exchange_calendar", "possibly_stale"}
    assert "Calendar-day heuristic" in payload["data_quality"]["freshness_note"]


def test_market_rejects_invalid_ticker_characters():
    with TestClient(app) as client:
        response = client.get("/api/market/RELIANCE%3BSELECT?period=1mo")
    assert response.status_code == 422
    assert "valid ticker" in response.json()["detail"]


def test_health_includes_utc_check_timestamp():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["checked_at"].endswith("+00:00")


def test_history_returns_clear_503_when_database_query_fails(monkeypatch):
    import app.main as main_module

    class BrokenQuery:
        def order_by(self, *args, **kwargs):
            raise RuntimeError("database offline")

    class BrokenSession:
        def query(self, *args, **kwargs):
            return BrokenQuery()
        def rollback(self):
            pass
        def close(self):
            pass

    def override_db():
        yield BrokenSession()

    app.dependency_overrides[main_module.get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/history")
        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(main_module.get_db, None)


def test_prediction_is_returned_even_when_history_cannot_be_saved(monkeypatch):
    import app.main as main_module

    monkeypatch.setattr(main_module, "predict", lambda symbol, **kwargs: {
        "symbol": symbol.upper(), "latest_close": 100.0,
        "predicted_direction": "UP", "model": "test-model",
        "test_accuracy": 0.6, "explanation": "test result"
    })

    class BrokenSession:
        def add(self, item):
            pass
        def commit(self):
            raise RuntimeError("database offline")
        def rollback(self):
            pass
        def close(self):
            pass

    def override_db():
        yield BrokenSession()

    app.dependency_overrides[main_module.get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/predict/RELIANCE.NS")
        assert response.status_code == 200
        assert response.json()["predicted_direction"] == "UP"
        assert response.json()["history_saved"] is False
    finally:
        app.dependency_overrides.pop(main_module.get_db, None)


def test_symbol_watchlist_has_common_indian_market_symbols():
    with TestClient(app) as client:
        response = client.get("/api/symbols")
    assert response.status_code == 200
    payload = response.json()
    symbols = {item["symbol"] for item in payload["symbols"]}
    assert "^NSEI" in symbols
    assert "RELIANCE.NS" in symbols
    assert "TCS.NS" in symbols
    assert payload["note"]


def test_symbols_endpoint_returns_expected_market_watchlist():
    with TestClient(app) as client:
        response = client.get("/api/symbols")
    assert response.status_code == 200
    payload = response.json()
    symbols = {item["symbol"] for item in payload["symbols"]}
    assert "^NSEI" in symbols
    assert "RELIANCE.NS" in symbols
    assert payload["note"]


def test_symbols_endpoint_includes_names_and_kinds():
    with TestClient(app) as client:
        response = client.get("/api/symbols")
    assert response.status_code == 200
    assert all(item.get("name") and item.get("kind") for item in response.json()["symbols"])


def test_backtest_endpoint_returns_risk_and_comparison_metrics(monkeypatch):
    import pandas as pd
    import app.main as main_module

    index = pd.date_range("2024-01-01", periods=80, freq="B")
    close = pd.Series([100 + i * 0.25 + (i % 5) * 0.1 for i in range(80)], index=index)
    frame = pd.DataFrame({
        "Close": close,
        "SMA20": close.rolling(20, min_periods=1).mean(),
        "SMA50": close.rolling(50, min_periods=1).mean(),
    }, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/backtest/RELIANCE.NS?period=1y")
    assert response.status_code == 200
    result = response.json()
    assert result["symbol"] == "RELIANCE.NS"
    assert result["observations"] == 80
    assert "strategy_return_pct" in result and "buy_hold_return_pct" in result
    assert "max_drawdown_pct" in result and "sharpe_ratio" in result
    assert "annualized_return_pct" in result
    assert "sortino_ratio" in result and "calmar_ratio" in result
    assert 0 <= result["market_exposure_pct"] <= 100
    assert result["position_entries"] >= 0
    assert result["assumptions"]


def test_backtest_rejects_too_little_history(monkeypatch):
    import pandas as pd
    import app.main as main_module
    index = pd.date_range("2024-01-01", periods=20, freq="B")
    frame = pd.DataFrame({"Close": range(100, 120), "SMA20": range(100, 120), "SMA50": range(100, 120)}, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/backtest/TCS.NS")
    assert response.status_code == 422
    assert "60 clean observations" in response.json()["detail"]


def test_live_status_does_not_expose_access_token(monkeypatch):
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "private-test-token")
    with TestClient(app) as client:
        response = client.get("/api/live/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert "private-test-token" not in response.text
    assert payload["provider"] == "Upstox V3 LTP"


def test_live_quotes_requires_upstox_token(monkeypatch):
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    with TestClient(app) as client:
        response = client.get("/api/live/quotes?symbols=RELIANCE.NS")
    assert response.status_code == 503
    assert "UPSTOX_ACCESS_TOKEN" in response.json()["detail"]


def test_live_quotes_parses_upstox_ltp_response(monkeypatch):
    import app.upstox as upstox_module

    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "test-token")

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"status": "success", "data": {
                "NSE_EQ:INE002A01018": {
                    "last_price": 1234.5,
                    "instrument_token": "NSE_EQ|INE002A01018",
                    "ltq": 10,
                    "volume": 9000,
                    "cp": 1200.0,
                }
            }}

    def fake_get(url, params, headers, timeout):
        assert url == upstox_module.UPSTOX_LTP_URL
        assert "Bearer test-token" == headers["Authorization"]
        assert "NSE_EQ|INE002A01018" in params["instrument_key"]
        return FakeResponse()

    monkeypatch.setattr(upstox_module.httpx, "get", fake_get)
    with TestClient(app) as client:
        response = client.get("/api/live/quotes?symbols=RELIANCE.NS")
    assert response.status_code == 200
    quote = response.json()["quotes"][0]
    assert quote["available"] is True
    assert quote["last_price"] == 1234.5
    assert quote["change"] == 34.5
    assert quote["change_pct"] == 2.875
    assert response.json()["provider"] == "Upstox V3 LTP"


def test_live_quotes_rejects_unconfigured_symbol(monkeypatch):
    with TestClient(app) as client:
        response = client.get("/api/live/quotes?symbols=UNKNOWN.NS")
    assert response.status_code == 422
    assert "No Upstox instrument key configured" in response.json()["detail"]


def test_readiness_endpoint_reports_upstox_and_stream_state(monkeypatch):
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "private-readiness-token")
    monkeypatch.setenv("UPSTOX_STREAM_ENABLED", "false")
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "not_ready"}
    assert payload["checks"]["upstox_token_configured"] is True
    assert payload["checks"]["stream_connection"] == "disabled"
    assert "private-readiness-token" not in response.text


def test_live_status_reports_rest_fallback_when_stream_has_no_fresh_ticks(monkeypatch):
    import app.main as main_module
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("UPSTOX_STREAM_ENABLED", "true")
    monkeypatch.setattr(main_module.stream_manager, "status", lambda: {
        "enabled": True, "configured": True, "connection": "connected",
        "feed_health": "awaiting_first_tick", "tick_age_seconds": None,
    })
    with TestClient(app) as client:
        response = client.get("/api/live/status")
    assert response.status_code == 200
    assert response.json()["mode"] == "rest_snapshot_fallback"


def test_readiness_allows_research_only_mode_without_upstox_token(monkeypatch):
    monkeypatch.setenv("UPSTOX_STREAM_REQUIRED", "false")
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"]["stream_required_for_readiness"] is False


def test_readiness_returns_503_when_required_upstox_stream_is_not_ready(monkeypatch):
    monkeypatch.setenv("UPSTOX_STREAM_REQUIRED", "true")
    monkeypatch.setenv("UPSTOX_STREAM_ENABLED", "true")
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["upstox_token_configured"] is False


def test_live_status_reports_websocket_capacity_without_credentials(monkeypatch):
    import app.main as main_module

    monkeypatch.setenv("MAX_LIVE_WS_CLIENTS", "23")
    with TestClient(app) as client:
        response = client.get("/api/live/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["websocket_client_limit"] == 23
    assert isinstance(payload["websocket_clients"], int)
    assert "private-token-value" not in response.text


def test_websocket_client_limit_is_bounded(monkeypatch):
    import app.main as main_module

    monkeypatch.setenv("MAX_LIVE_WS_CLIENTS", "999999")
    assert main_module.max_live_ws_clients() == 1000
    monkeypatch.setenv("MAX_LIVE_WS_CLIENTS", "not-a-number")
    assert main_module.max_live_ws_clients() == 100
    monkeypatch.setenv("MAX_LIVE_WS_CLIENTS", "0")
    assert main_module.max_live_ws_clients() == 1


def test_live_websocket_rejects_connections_when_capacity_is_full(monkeypatch):
    from starlette.websockets import WebSocketDisconnect
    import app.main as main_module

    monkeypatch.setattr(main_module, "max_live_ws_clients", lambda: 1)
    main_module.live_ws_clients.add(object())
    try:
        with TestClient(app) as client:
            try:
                with client.websocket_connect("/api/live/stream") as websocket:
                    websocket.receive_json()
            except WebSocketDisconnect as exc:
                assert exc.code == 1013
            else:
                raise AssertionError("Expected overloaded WebSocket connection to be rejected")
    finally:
        main_module.live_ws_clients.clear()


def test_expensive_routes_are_rate_limited_with_retry_after(monkeypatch):
    import app.main as main_module
    monkeypatch.setenv("RATE_LIMIT_HISTORY_PER_WINDOW", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    main_module.limiter.clear()
    with TestClient(app) as client:
        first = client.get("/api/market/RELIANCE.NS?period=invalid")
        second = client.get("/api/market/TCS.NS?period=invalid")
    assert first.status_code == 422
    assert second.status_code == 429
    assert second.headers["retry-after"]
    assert second.json()["bucket"] == "history"
    main_module.limiter.clear()


def test_rate_limit_buckets_do_not_block_health_or_docs(monkeypatch):
    import app.main as main_module
    monkeypatch.setenv("RATE_LIMIT_HISTORY_PER_WINDOW", "1")
    main_module.limiter.clear()
    with TestClient(app) as client:
        client.get("/api/market/RELIANCE.NS?period=invalid")
        assert client.get("/health").status_code == 200
        assert client.get("/docs").status_code == 200
    main_module.limiter.clear()


def test_rate_limiter_sliding_window_expires_old_attempts():
    from app.rate_limit import SlidingWindowLimiter
    clock = [100.0]
    limiter_instance = SlidingWindowLimiter(clock=lambda: clock[0])
    assert limiter_instance.check("client", "quotes", 1, 10) == (True, 0)
    assert limiter_instance.check("client", "quotes", 1, 10)[0] is False
    clock[0] = 111.0
    assert limiter_instance.check("client", "quotes", 1, 10) == (True, 0)


def test_live_quotes_reuses_short_cache_for_identical_watchlist(monkeypatch):
    import app.upstox as upstox_module
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "cache-test-token")
    monkeypatch.setenv("UPSTOX_QUOTE_CACHE_SECONDS", "5")
    upstox_module.clear_quote_cache()
    calls = {"count": 0}

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"status": "success", "data": {
                "NSE_EQ:INE002A01018": {
                    "last_price": 100.0,
                    "instrument_token": "NSE_EQ|INE002A01018",
                    "cp": 98.0,
                }
            }}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse()

    monkeypatch.setattr(upstox_module.httpx, "get", fake_get)
    first = upstox_module.get_live_quotes(["RELIANCE.NS"])
    second = upstox_module.get_live_quotes(["RELIANCE.NS"])
    assert calls["count"] == 1
    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is True
    upstox_module.clear_quote_cache()


def test_live_quotes_cache_can_be_disabled(monkeypatch):
    import app.upstox as upstox_module
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "cache-test-token")
    monkeypatch.setenv("UPSTOX_QUOTE_CACHE_SECONDS", "0")
    upstox_module.clear_quote_cache()
    calls = {"count": 0}

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"status": "success", "data": {
                "NSE_EQ:INE002A01018": {
                    "last_price": 100.0,
                    "instrument_token": "NSE_EQ|INE002A01018",
                    "cp": 98.0,
                }
            }}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse()

    monkeypatch.setattr(upstox_module.httpx, "get", fake_get)
    upstox_module.get_live_quotes(["RELIANCE.NS"])
    upstox_module.get_live_quotes(["RELIANCE.NS"])
    assert calls["count"] == 2
    upstox_module.clear_quote_cache()


def test_market_csv_export_returns_downloadable_history(monkeypatch):
    import pandas as pd
    import app.main as main_module

    index = pd.to_datetime(["2026-10-12", "2026-10-13"])
    fake = pd.DataFrame({
        "Open": [100.0, 101.0], "High": [103.0, 104.0],
        "Low": [99.0, 100.0], "Close": [102.0, 103.0],
        "Volume": [1000, 1200], "RSI": [50.0, 55.0],
        "SMA20": [101.0, 101.5], "SMA50": [99.0, 99.5],
    }, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: fake)
    with TestClient(app) as client:
        response = client.get("/api/market/RELIANCE.NS/export.csv?period=1mo")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="RELIANCE.NS-1mo-history.csv"' in response.headers["content-disposition"]
    assert "Close" in response.text and "103.0" in response.text
    assert "2026-10-13" in response.text


def test_market_csv_export_validates_period_before_provider_call():
    with TestClient(app) as client:
        response = client.get("/api/market/RELIANCE.NS/export.csv?period=banana")
    assert response.status_code == 422


def test_risk_endpoint_returns_historical_var_cvar_and_volatility(monkeypatch):
    import pandas as pd
    import app.main as main_module

    index = pd.date_range("2024-01-01", periods=90, freq="B")
    close = pd.Series([100.0 * (1.001 ** i) * (1 + (0.012 if i % 9 == 0 else -0.006 if i % 7 == 0 else 0.001)) for i in range(90)], index=index)
    frame = pd.DataFrame({"Close": close}, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/risk/RELIANCE.NS?period=1y")
    assert response.status_code == 200
    result = response.json()
    assert result["symbol"] == "RELIANCE.NS"
    assert result["observations"] >= 20
    for key in ("daily_var_95_pct", "daily_cvar_95_pct", "daily_var_99_pct", "daily_cvar_99_pct", "annualized_volatility_pct", "annualized_downside_volatility_pct", "historical_max_drawdown_pct"):
        assert isinstance(result[key], float)
    assert result["daily_cvar_95_pct"] <= result["daily_var_95_pct"]
    assert result["daily_cvar_99_pct"] <= result["daily_var_99_pct"]
    assert result["assumptions"]


def test_risk_endpoint_rejects_invalid_period_before_provider_call():
    with TestClient(app) as client:
        response = client.get("/api/risk/RELIANCE.NS?period=banana")
    assert response.status_code == 422


def test_risk_endpoint_rejects_insufficient_history(monkeypatch):
    import pandas as pd
    import app.main as main_module
    frame = pd.DataFrame({"Close": [100.0 + i for i in range(10)]}, index=pd.date_range("2024-01-01", periods=10, freq="B"))
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/risk/TCS.NS")
    assert response.status_code == 422
    assert "30 closing-price observations" in response.json()["detail"]


def test_position_size_respects_risk_and_allocation_caps():
    with TestClient(app) as client:
        response = client.get("/api/position-size", params={
            "portfolio_value": 100000, "risk_percent": 1,
            "entry_price": 100, "stop_price": 95,
            "max_allocation_percent": 20,
        })
    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_budget"] == 1000
    assert payload["shares_by_risk_limit"] == 200
    assert payload["shares_by_allocation_limit"] == 200
    assert payload["recommended_quantity_for_plan"] == 200
    assert payload["capital_required"] == 20000
    assert payload["planned_loss_at_stop"] == 1000


def test_position_size_allocation_cap_can_limit_quantity():
    with TestClient(app) as client:
        response = client.get("/api/position-size", params={
            "portfolio_value": 100000, "risk_percent": 1,
            "entry_price": 100, "stop_price": 90,
            "max_allocation_percent": 5,
        })
    assert response.status_code == 200
    payload = response.json()
    assert payload["shares_by_risk_limit"] == 100
    assert payload["shares_by_allocation_limit"] == 50
    assert payload["recommended_quantity_for_plan"] == 50
    assert payload["planned_loss_at_stop"] == 500


def test_position_size_rejects_stop_at_or_above_entry():
    with TestClient(app) as client:
        response = client.get("/api/position-size", params={
            "portfolio_value": 100000, "entry_price": 100, "stop_price": 100,
        })
    assert response.status_code == 422
    assert "stop_price must be below" in response.json()["detail"]


def test_position_size_validates_risk_percentage():
    with TestClient(app) as client:
        response = client.get("/api/position-size", params={
            "portfolio_value": 100000, "risk_percent": 6,
            "entry_price": 100, "stop_price": 95,
        })
    assert response.status_code == 422


def test_backtest_models_transaction_costs_and_reports_gross_and_net(monkeypatch):
    import pandas as pd
    import app.main as main_module

    close = [100.0 + i for i in range(70)]
    index = pd.date_range("2026-01-01", periods=len(close), freq="B")
    sma20 = [90.0 if i < 30 else 110.0 for i in range(len(close))]
    sma50 = [100.0] * len(close)
    fake = pd.DataFrame({"Close": close, "SMA20": sma20, "SMA50": sma50}, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: fake)
    with TestClient(app) as client:
        gross = client.get("/api/backtest/RELIANCE.NS?period=3mo&cost_bps=0")
        net = client.get("/api/backtest/RELIANCE.NS?period=3mo&cost_bps=10")
    assert gross.status_code == 200
    assert net.status_code == 200
    assert gross.json()["gross_strategy_return_pct"] == gross.json()["strategy_return_pct"]
    assert net.json()["strategy_return_pct"] <= gross.json()["strategy_return_pct"]
    assert net.json()["cost_bps_one_way"] == 10.0
    assert net.json()["turnover_events"] >= 1
    assert net.json()["estimated_transaction_cost_pct"] > 0


def test_backtest_rejects_unreasonable_transaction_cost(monkeypatch):
    with TestClient(app) as client:
        response = client.get("/api/backtest/RELIANCE.NS?cost_bps=101")
    assert response.status_code == 422


def test_system_status_reports_safe_diagnostics_without_secrets():
    with TestClient(app) as client:
        response = client.get("/api/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "BharatStock AI API"
    assert payload["database"] in {"connected", "unavailable"}
    assert "token_configured" in payload["upstox"]
    assert isinstance(payload["dependencies"], dict)
    assert "UPSTOX_ACCESS_TOKEN" not in str(payload)
    assert "secret" not in str(payload).lower() or payload["security_note"]
    assert payload["checked_at"].endswith("+00:00")


def test_system_status_reports_dependency_checks_as_booleans():
    with TestClient(app) as client:
        payload = client.get("/api/system/status").json()
    assert set(payload["dependencies"]) == {"fastapi", "pandas", "numpy", "sklearn", "sqlalchemy"}
    assert all(isinstance(available, bool) for available in payload["dependencies"].values())



def test_scenario_stress_calculates_hypothetical_position_loss(monkeypatch):
    import pandas as pd
    import app.main as main_module
    frame = pd.DataFrame({"Close": [100.0, 120.0]})
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/stress/RELIANCE.NS?shock_pct=-10&quantity=5&period=1y")
    assert response.status_code == 200
    payload = response.json()
    assert payload["reference_price"] == 120.0
    assert payload["scenario_price"] == 108.0
    assert payload["current_position_value"] == 600.0
    assert payload["scenario_position_value"] == 540.0
    assert payload["profit_loss"] == -60.0
    assert "not a forecast" in payload["disclaimer"]


def test_scenario_stress_accepts_positive_shock(monkeypatch):
    import pandas as pd
    import app.main as main_module
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: pd.DataFrame({"Close": [100.0]}))
    with TestClient(app) as client:
        response = client.get("/api/stress/TCS.NS?shock_pct=5&quantity=2")
    assert response.status_code == 200
    assert response.json()["profit_loss"] == 10.0


def test_scenario_stress_rejects_shock_outside_bounds():
    with TestClient(app) as client:
        response = client.get("/api/stress/TCS.NS?shock_pct=101")
    assert response.status_code == 422


def test_scenario_stress_reports_missing_price_data(monkeypatch):
    import pandas as pd
    import app.main as main_module
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: pd.DataFrame({"Close": []}))
    with TestClient(app) as client:
        response = client.get("/api/stress/TCS.NS")
    assert response.status_code == 422
    assert "unavailable" in response.json()["detail"]


def test_backtest_csv_export_contains_metrics_and_safe_headers(monkeypatch):
    import pandas as pd
    import numpy as np
    import app.main as main_module

    index = pd.date_range("2025-01-01", periods=90, freq="B")
    close = pd.Series(100 + np.arange(90) * 0.2 + np.sin(np.arange(90) / 4), index=index)
    fake = pd.DataFrame({
        "Close": close,
        "SMA20": close.rolling(20, min_periods=1).mean(),
        "SMA50": close.rolling(50, min_periods=1).mean(),
    }, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: fake)
    with TestClient(app) as client:
        response = client.get("/api/backtest/RELIANCE.NS/export.csv?period=3mo&cost_bps=10")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert 'filename="RELIANCE.NS-3mo-backtest.csv"' in response.headers["content-disposition"]
    assert "strategy_return_pct" in response.text
    assert "assumptions" in response.text
    assert "X-Content-Type-Options" in response.headers


def test_backtest_csv_export_validates_query_before_provider_call(monkeypatch):
    import app.main as main_module

    def should_not_fetch(*args, **kwargs):
        raise AssertionError("provider should not be called for invalid period")

    monkeypatch.setattr(main_module, "fetch_history", should_not_fetch)
    with TestClient(app) as client:
        response = client.get("/api/backtest/RELIANCE.NS/export.csv?period=invalid")
    assert response.status_code == 422



def test_risk_csv_export_contains_risk_metrics_and_safe_headers(monkeypatch):
    import pandas as pd
    import app.main as main_module

    index = pd.date_range("2025-01-01", periods=80, freq="B")
    close = pd.Series([100 + i * 0.15 + (i % 7) * 0.2 for i in range(80)], index=index)
    frame = pd.DataFrame({"Close": close}, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/risk/RELIANCE.NS/export.csv?period=1y")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="RELIANCE.NS-1y-risk.csv"' in response.headers["content-disposition"]
    assert "daily_var_95_pct" in response.text
    assert "historical_max_drawdown_pct" in response.text
    assert "RELIANCE.NS" in response.text
    assert response.headers["cache-control"] == "no-store"


def test_risk_csv_export_rejects_invalid_period_before_fetch():
    with TestClient(app) as client:
        response = client.get("/api/risk/TCS.NS/export.csv?period=all-time")
    assert response.status_code == 422


def test_risk_csv_export_returns_clear_error_for_insufficient_history(monkeypatch):
    import pandas as pd
    import app.main as main_module

    index = pd.date_range("2025-01-01", periods=10, freq="B")
    frame = pd.DataFrame({"Close": range(100, 110)}, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/risk/TCS.NS/export.csv?period=3mo")
    assert response.status_code == 422
    assert "30 closing-price observations" in response.json()["detail"]


def test_backtest_equity_curve_export_contains_daily_curves_and_safe_headers(monkeypatch):
    import pandas as pd
    import app.main as main_module

    index = pd.date_range("2025-01-01", periods=80, freq="B")
    close = pd.Series([100 + i * 0.2 + (i % 4) * 0.1 for i in range(80)], index=index)
    frame = pd.DataFrame({
        "Close": close,
        "SMA20": close.rolling(20, min_periods=1).mean(),
        "SMA50": close.rolling(50, min_periods=1).mean(),
    }, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/backtest/RELIANCE.NS/equity.csv?period=1y&cost_bps=10")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="RELIANCE.NS-1y-equity-curve.csv"' in response.headers["content-disposition"]
    assert "strategy_net_equity_base_1" in response.text
    assert "buy_hold_equity_base_1" in response.text
    assert len(response.text.strip().splitlines()) == 81
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_backtest_equity_curve_export_validates_period_before_provider_call(monkeypatch):
    import app.main as main_module

    def should_not_fetch(*args, **kwargs):
        raise AssertionError("provider should not be called for invalid period")

    monkeypatch.setattr(main_module, "fetch_history", should_not_fetch)
    with TestClient(app) as client:
        response = client.get("/api/backtest/TCS.NS/equity.csv?period=all")
    assert response.status_code == 422


def test_backtest_equity_curve_export_rejects_insufficient_history(monkeypatch):
    import pandas as pd
    import app.main as main_module

    index = pd.date_range("2025-01-01", periods=12, freq="B")
    frame = pd.DataFrame({"Close": range(100, 112), "SMA20": range(100, 112), "SMA50": range(100, 112)}, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/backtest/TCS.NS/equity.csv?period=3mo")
    assert response.status_code == 422
    assert "60 clean observations" in response.json()["detail"]


def test_market_freshness_marks_old_history_as_possibly_stale(monkeypatch):
    import pandas as pd
    import app.main as main_module

    old_index = pd.to_datetime(["2020-01-02", "2020-01-03"])
    fake = pd.DataFrame({"Close": [100.0, 101.0]}, index=old_index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: fake)
    with TestClient(app) as client:
        response = client.get("/api/market/RELIANCE.NS?period=1mo")
    assert response.status_code == 200
    quality = response.json()["data_quality"]
    assert quality["freshness"] == "possibly_stale"
    assert quality["calendar_days_since_latest"] > 10


def test_market_freshness_never_returns_negative_age_for_future_provider_date(monkeypatch):
    import pandas as pd
    from datetime import datetime, timedelta, timezone
    import app.main as main_module

    future_date = (datetime.now(timezone.utc).date() + timedelta(days=2)).isoformat()
    fake = pd.DataFrame({"Close": [100.0]}, index=pd.to_datetime([future_date]))
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: fake)
    with TestClient(app) as client:
        response = client.get("/api/market/RELIANCE.NS?period=1mo")
    assert response.status_code == 200
    assert response.json()["data_quality"]["calendar_days_since_latest"] == 0


def test_correlation_analysis_returns_symmetric_matrix(monkeypatch):
    import pandas as pd
    import app.main as main_module

    index = pd.date_range("2025-01-01", periods=40, freq="B")
    closes_a = [100.0]
    closes_b = [200.0]
    for i in range(1, len(index)):
        closes_a.append(closes_a[-1] * (1.0 + (0.002 if i % 2 else -0.001)))
        closes_b.append(closes_b[-1] * (1.0 + (0.001 if i % 3 else -0.002)))
    frames = {
        "AAA.NS": pd.DataFrame({"Close": closes_a}, index=index),
        "BBB.NS": pd.DataFrame({"Close": closes_b}, index=index),
    }
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frames[symbol])
    with TestClient(app) as client:
        response = client.get("/api/analysis/correlation?symbols=AAA.NS,BBB.NS&period=1y")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbols"] == ["AAA.NS", "BBB.NS"]
    assert payload["observations"] == 39
    assert payload["matrix"][0]["AAA.NS"] == 1.0
    assert payload["matrix"][1]["BBB.NS"] == 1.0
    assert payload["matrix"][0]["BBB.NS"] == payload["matrix"][1]["AAA.NS"]


def test_correlation_analysis_requires_two_to_eight_distinct_symbols(monkeypatch):
    import app.main as main_module
    monkeypatch.setattr(main_module, "fetch_history", lambda *args: (_ for _ in ()).throw(AssertionError("provider should not be called")))
    with TestClient(app) as client:
        too_few = client.get("/api/analysis/correlation?symbols=RELIANCE.NS")
        duplicates = client.get("/api/analysis/correlation?symbols=RELIANCE.NS,RELIANCE.NS")
        too_many = client.get("/api/analysis/correlation?symbols=A,B,C,D,E,F,G,H,I")
    assert too_few.status_code == 422
    assert duplicates.status_code == 422
    assert too_many.status_code == 422


def test_correlation_analysis_rejects_short_history(monkeypatch):
    import pandas as pd
    import app.main as main_module
    index = pd.date_range("2025-01-01", periods=12, freq="B")
    frame = pd.DataFrame({"Close": range(100, 112)}, index=index)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.get("/api/analysis/correlation?symbols=AAA.NS,BBB.NS")
    assert response.status_code == 422
    assert "20 daily returns" in response.json()["detail"]


def test_index_trade_idea_uses_provider_history_and_persists(monkeypatch):
    import pandas as pd
    import app.main as main_module

    dates = pd.date_range("2026-01-01", periods=80, freq="B")
    close = [25000.0 + i * 0.5 for i in range(80)]
    frame = pd.DataFrame({
        "Open": [v - 0.2 for v in close], "High": [v + 1.0 for v in close],
        "Low": [v - 1.0 for v in close], "Close": close, "Volume": [1000] * 80,
        "SMA20": [v - 2.0 for v in close], "SMA50": [v - 5.0 for v in close],
        "RSI": [55.0] * 80, "ATR": [2.0] * 80,
    }, index=dates)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.post("/api/trades/suggest/%5ENSEI")
        assert response.status_code == 200, response.text
        idea = response.json()
        assert idea["symbol"] == "^NSEI"
        assert idea["signal"] == "BULLISH_WATCH"
        assert idea["entry_price"] == close[-1]
        assert idea["stop_price"] < idea["entry_price"] < idea["target_price"]
        assert "not a guarantee" in idea["disclaimer"]
        listed = client.get("/api/trades?symbol=%5ENSEI")
        assert listed.status_code == 200
        assert any(item["id"] == idea["id"] for item in listed.json())
        # Re-analyzing the same symbol refreshes the active watch instead of
        # adding another duplicate active journal card.
        repeated = client.post("/api/trades/suggest/%5ENSEI")
        assert repeated.status_code == 200, repeated.text
        assert repeated.json()["id"] == idea["id"]
        listed_again = client.get("/api/trades?symbol=%5ENSEI&status=watching")
        assert listed_again.status_code == 200
        assert len(listed_again.json()) == 1
        changed = client.patch(f"/api/trades/{idea['id']}?status=closed")
        assert changed.status_code == 200
        assert changed.json()["status"] == "closed"


def test_trade_idea_rejects_malformed_symbol():
    with TestClient(app) as client:
        response = client.post("/api/trades/suggest/BAD%20SYMBOL")
    assert response.status_code == 422


def test_research_status_discloses_real_models_and_no_synthetic_data():
    with TestClient(app) as client:
        response = client.get("/api/research/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["no_synthetic_market_data"] is True
    assert "Random Forest baseline" in payload["models"]
    assert payload["demo_trading_gate"]


def test_news_event_ingestion_enforces_timezone_and_availability_policy():
    with TestClient(app) as client:
        bad = client.post("/api/news/events", json={"symbol":"RELIANCE.NS", "headline":"Company reports strong growth and record profit", "published_at":"2026-10-30T10:05:00"})
        assert bad.status_code == 422
        good = client.post("/api/news/events", json={"symbol":"RELIANCE.NS", "headline":"Company reports strong growth and record profit", "published_at":"2026-10-30T10:05:00+05:30", "source":"test-source", "source_url":"https://example.com/news/1", "event_type":"earnings"})
        assert good.status_code == 200
        payload = good.json()
        assert payload["sentiment_score"] > 0
        assert payload["available_at"] >= payload["published_at"]
        listed = client.get("/api/news/events?symbol=RELIANCE.NS")
        assert listed.status_code == 200
        assert any(event["id"] == payload["id"] for event in listed.json()["events"])


def test_intraday_research_rejects_bad_interval_before_provider_call():
    with TestClient(app) as client:
        response = client.get("/api/research/intraday/RELIANCE.NS?instrument_key=NSE_EQ%7CINE000000000&interval=7")
    assert response.status_code == 422


def test_upstox_news_sync_persists_timestamped_articles_without_external_call(monkeypatch):
    import app.main as main_module
    from datetime import datetime, timezone
    unique_article_url = f"https://example.com/article-test-{datetime.now(timezone.utc).timestamp()}"
    monkeypatch.setattr(main_module, "fetch_upstox_news", lambda keys: {
        "provider": "Upstox News API", "fetched_at": datetime.now(timezone.utc).isoformat(),
        "requested_instruments": keys, "count": 1, "history_limit": "past seven days",
        "articles": [{"instrument_key": keys[0], "headline": "Reliance reports strong growth and profit", "summary": "", "source_url": unique_article_url, "thumbnail_url": "", "published_at": "2026-10-30T04:00:00+00:00", "source": "Upstox News API", "event_type": "news", "sentiment_score": 0.4}]
    })
    with TestClient(app) as client:
        response = client.post("/api/news/upstox/sync?instrument_keys=NSE_EQ%7CINE002A01018")
        assert response.status_code == 200
        payload = response.json()
        assert payload["inserted"] == 1
        assert payload["provider"] == "Upstox News API"
        second = client.post("/api/news/upstox/sync?instrument_keys=NSE_EQ%7CINE002A01018")
        assert second.status_code == 200
        assert second.json()["duplicates_skipped"] == 1


def test_index_trade_idea_rejects_implausible_index_price(monkeypatch):
    import pandas as pd
    import app.main as main_module

    dates = pd.date_range("2026-01-01", periods=80, freq="B")
    close = [100.0 + i * 0.5 for i in range(80)]
    frame = pd.DataFrame({
        "Open": [v - 0.2 for v in close], "High": [v + 1.0 for v in close],
        "Low": [v - 1.0 for v in close], "Close": close, "Volume": [1000] * 80,
        "SMA20": [v - 2.0 for v in close], "SMA50": [v - 5.0 for v in close],
        "RSI": [55.0] * 80, "ATR": [2.0] * 80,
    }, index=dates)
    monkeypatch.setattr(main_module, "fetch_history", lambda symbol, period: frame)
    with TestClient(app) as client:
        response = client.post("/api/trades/suggest/%5ENSEI")
        assert response.status_code == 422
        assert "outside the sanity range" in response.json()["detail"]
        listed = client.get("/api/trades?symbol=%5ENSEI&status=watching")
        assert listed.status_code == 200
        assert listed.json() == []
