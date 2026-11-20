from app.upstox_stream import UpstoxStreamManager
from app.upstox import _instrument_map


def test_stream_manager_consumes_upstox_ltpc_tick():
    manager = UpstoxStreamManager()
    manager._consume({
        "type": "live_feed",
        "feeds": {
            "NSE_EQ|INE002A01018": {"ltpc": {"ltp": 2500.0, "cp": 2450.0, "ltq": "12", "ltt": "123"}}
        },
        "currentTs": "123",
    }, _instrument_map())
    snapshot = manager.snapshot()
    assert snapshot["sequence"] == 1
    quote = next(q for q in snapshot["quotes"] if q["symbol"] == "RELIANCE.NS")
    assert quote["last_price"] == 2500.0
    assert quote["change"] == 50.0
    assert quote["change_pct"] == round(50 / 2450 * 100, 4)


def test_stream_manager_ignores_market_status_frames():
    manager = UpstoxStreamManager()
    manager._consume({"type": "market_info", "feeds": {}}, _instrument_map())
    snapshot = manager.snapshot()
    assert snapshot["sequence"] == 0
    assert snapshot["quotes"] == []


def test_stream_status_never_exposes_token(monkeypatch):
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "secret-value")
    status = UpstoxStreamManager().status()
    assert status["configured"] is True
    assert "secret-value" not in str(status)


def test_websocket_stream_endpoint_sends_connection_state(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("UPSTOX_STREAM_ENABLED", "false")
    with TestClient(app) as client:
        with client.websocket_connect("/api/live/stream") as websocket:
            packet = websocket.receive_json()
    assert packet["type"] == "quotes"
    assert packet["mode"] == "websocket_ltpc"
    assert packet["connection"] == "disabled"
    assert packet["server_time"]


def test_stream_snapshot_does_not_include_access_token(monkeypatch):
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "very-secret-token")
    manager = UpstoxStreamManager()
    payload = manager.snapshot()
    assert "very-secret-token" not in str(payload)
    assert payload["type"] == "quotes"


def test_stream_status_distinguishes_connected_socket_from_fresh_ticks(monkeypatch):
    monkeypatch.setenv("UPSTOX_STREAM_ENABLED", "true")
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "test-token")
    manager = UpstoxStreamManager()
    manager._state = "connected"
    assert manager.status()["feed_health"] == "awaiting_first_tick"
    manager._updated_at = "2000-01-01T00:00:00+00:00"
    status = manager.status()
    assert status["feed_health"] == "stale"
    assert status["tick_age_seconds"] > 30


def test_stream_status_reports_recent_tick_as_live():
    from datetime import datetime, timezone
    manager = UpstoxStreamManager()
    manager._state = "connected"
    manager._updated_at = datetime.now(timezone.utc).isoformat()
    assert manager.status()["feed_health"] == "live"
    assert manager.snapshot()["feed_health"] == "live"


def test_sensex_is_configured_for_upstox_live_quotes():
    mapping = _instrument_map()
    assert mapping["^BSESN"]["name"] == "SENSEX"
    assert mapping["^BSESN"]["instrument_key"] == "BSE_INDEX|SENSEX"


def test_authorization_uses_fresh_v3_endpoint_and_returns_wss_url(monkeypatch):
    import json
    from app import upstox_stream

    seen = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "status": "success",
                "data": {"authorized_redirect_uri": "wss://feed.upstox.com/one-time"},
            }).encode()

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["authorization"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(upstox_stream.urllib.request, "urlopen", fake_urlopen)
    result = upstox_stream._get_authorized_feed_url("test-token")

    assert result == "wss://feed.upstox.com/one-time"
    assert seen["url"] == "https://api.upstox.com/v3/feed/market-data-feed/authorize"
    assert seen["authorization"] == "Bearer test-token"
    assert seen["timeout"] == 10


def test_authorization_rejects_non_upstox_websocket_url(monkeypatch):
    import json
    import pytest
    from app import upstox_stream

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "status": "success",
                "data": {"authorized_redirect_uri": "wss://attacker.example/socket"},
            }).encode()

    monkeypatch.setattr(upstox_stream.urllib.request, "urlopen", lambda *_a, **_k: FakeResponse())
    with pytest.raises(RuntimeError, match="unexpected WebSocket URL"):
        upstox_stream._get_authorized_feed_url("test-token")
