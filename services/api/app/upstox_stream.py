"""Upstox Market Data Feed V3 streaming manager.

Uses Upstox's V3 authorize endpoint to obtain a fresh, single-use WebSocket
URL for each connection. The application owns the reconnect lifecycle so
only one WebSocket connection is active for this manager at a time.

Access tokens and authorized WebSocket URLs are never logged or returned.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .upstox import _instrument_map


class UpstoxAuthorizationError(RuntimeError):
    """Authentication/authorization failure that should not be retried."""


def _get_authorized_feed_url(token: str) -> str:
    """Get a fresh, single-use authorized V3 WebSocket URL from Upstox."""
    if not token:
        raise UpstoxAuthorizationError("Upstox access token is not configured.")

    request = urllib.request.Request(
        "https://api.upstox.com/v3/feed/market-data-feed/authorize",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "BharatStock-AI/1.0",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise UpstoxAuthorizationError(
                f"Upstox rejected WebSocket authorization: HTTP {exc.code}."
            ) from None
        raise RuntimeError(
            f"Upstox WebSocket authorization returned HTTP {exc.code}."
        ) from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Upstox WebSocket authorization failed: {type(exc).__name__}."
        ) from None

    if not isinstance(payload, dict):
        raise RuntimeError("Upstox returned an invalid authorization response.")

    data = payload.get("data")
    url = data.get("authorized_redirect_uri") if isinstance(data, dict) else None

    if not isinstance(url, str) or not url.strip():
        status = payload.get("status", "unknown")
        raise RuntimeError(
            f"Upstox did not return an authorized WebSocket URL (status={status})."
        )

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    # Only accept TLS WebSocket URLs on an actual Upstox-owned hostname.
    if (
        parsed.scheme != "wss"
        or not hostname
        or not (hostname == "upstox.com" or hostname.endswith(".upstox.com"))
        or parsed.username
        or parsed.password
    ):
        raise RuntimeError(
            "Upstox returned an unexpected WebSocket URL; connection was blocked."
        )

    return url


class UpstoxStreamManager:
    """Own one Upstox V3 stream and its sequential reconnect lifecycle."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._streamer: Any = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._fatal = threading.Event()

        self._state = "disabled"
        self._error: str | None = None
        self._updated_at: str | None = None
        self._sequence = 0
        self._quotes: dict[str, dict[str, Any]] = {}
        # Counters contain metadata only; never retain raw market-data payloads,
        # access tokens, or the one-time authorized WebSocket URL.
        self._diagnostics: dict[str, Any] = {
            "connection_attempts": 0,
            "authorization_successes": 0,
            "socket_open_events": 0,
            "subscription_key_count": 0,
            "subscription_event_at": None,
            "raw_messages_received": 0,
            "raw_message_bytes": 0,
            "raw_binary_messages": 0,
            "raw_text_messages": 0,
            "decoded_messages_received": 0,
            "messages_with_feeds": 0,
            "messages_without_feeds": 0,
            "feed_entries_received": 0,
            "valid_ltpc_records": 0,
            "unmatched_instrument_records": 0,
            "last_raw_message_at": None,
            "last_decoded_message_at": None,
            "last_feed_message_at": None,
            "last_message_type": None,
            "last_message_top_level_keys": [],
            "last_feed_fields": [],
            "last_instrument_keys_sample": [],
            "errors_received": 0,
            "close_events": 0,
            "last_error_at": None,
        }

    @staticmethod
    def _diagnostic_timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _record_raw_message(self, payload: Any) -> None:
        """Record WebSocket frame metadata without storing or logging its contents."""
        now = self._diagnostic_timestamp()
        if isinstance(payload, (bytes, bytearray, memoryview)):
            size = len(payload)
            kind = "raw_binary_messages"
        elif isinstance(payload, str):
            size = len(payload.encode("utf-8", errors="replace"))
            kind = "raw_text_messages"
        else:
            size = 0
            kind = None

        with self._lock:
            self._diagnostics["raw_messages_received"] += 1
            self._diagnostics["raw_message_bytes"] += size
            if kind:
                self._diagnostics[kind] += 1
            self._diagnostics["last_raw_message_at"] = now

    def _record_decoded_message_shape(self, message: Any) -> None:
        """Record decoded message structure only, never market values."""
        now = self._diagnostic_timestamp()
        top_keys = sorted(str(key) for key in message.keys())[:20] if isinstance(message, dict) else []
        message_type = message.get("type") if isinstance(message, dict) else type(message).__name__
        feeds = message.get("feeds") if isinstance(message, dict) else None

        with self._lock:
            self._diagnostics["decoded_messages_received"] += 1
            self._diagnostics["last_decoded_message_at"] = now
            self._diagnostics["last_message_type"] = (
                str(message_type)[:80] if message_type is not None else None
            )
            self._diagnostics["last_message_top_level_keys"] = top_keys
            if isinstance(feeds, dict):
                self._diagnostics["messages_with_feeds"] += 1
                self._diagnostics["feed_entries_received"] += len(feeds)
                self._diagnostics["last_feed_message_at"] = now
                first_feed = next(iter(feeds.values()), None)
                feed_fields = (
                    sorted(str(key) for key in first_feed.keys())[:20]
                    if isinstance(first_feed, dict)
                    else []
                )
                self._diagnostics["last_feed_fields"] = feed_fields
                self._diagnostics["last_instrument_keys_sample"] = [
                    str(key)[:100] for key in list(feeds.keys())[:5]
                ]
            else:
                self._diagnostics["messages_without_feeds"] += 1

    @staticmethod
    def _enabled() -> bool:
        return (
            os.getenv("UPSTOX_STREAM_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )

    def _freshness_locked(self) -> tuple[str, float | None]:
        """Classify tick freshness separately from socket connection state."""
        if not self._updated_at:
            if self._state in {
                "disabled",
                "not_configured",
                "stopped",
                "error",
                "reconnecting",
            }:
                return "unavailable", None
            return "awaiting_first_tick", None

        try:
            updated = datetime.fromisoformat(
                self._updated_at.replace("Z", "+00:00")
            )
            age = max(
                0.0,
                (
                    datetime.now(timezone.utc)
                    - updated.astimezone(timezone.utc)
                ).total_seconds(),
            )
        except (TypeError, ValueError):
            return "unknown", None

        try:
            threshold = max(
                5, int(os.getenv("UPSTOX_STALE_TICK_SECONDS", "30"))
            )
        except ValueError:
            threshold = 30

        return ("live" if age <= threshold else "stale"), round(age, 2)

    def status(self) -> dict[str, Any]:
        with self._lock:
            freshness, age = self._freshness_locked()
            return {
                "provider": "Upstox Market Data Feed V3",
                "mode": "websocket_ltpc",
                "enabled": self._enabled(),
                "configured": bool(
                    os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
                ),
                "connection": self._state,
                "feed_health": freshness,
                "tick_age_seconds": age,
                "last_tick_at": self._updated_at,
                "symbols_with_ticks": len(self._quotes),
                "error": self._error,
                "diagnostics": {
                    **self._diagnostics,
                    "last_message_top_level_keys": list(
                        self._diagnostics["last_message_top_level_keys"]
                    ),
                    "last_feed_fields": list(self._diagnostics["last_feed_fields"]),
                    "last_instrument_keys_sample": list(
                        self._diagnostics["last_instrument_keys_sample"]
                    ),
                },
            }

    def start(self) -> None:
        """Start the worker once; repeated calls do not create extra workers."""
        if not self._enabled():
            with self._lock:
                self._state = "disabled"
                self._error = None
            return

        if not os.getenv("UPSTOX_ACCESS_TOKEN", "").strip():
            with self._lock:
                self._state = "not_configured"
                self._error = (
                    "Set UPSTOX_ACCESS_TOKEN in the backend environment."
                )
            return

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._stop.clear()
            self._fatal.clear()
            self._state = "connecting"
            self._error = None
            self._thread = threading.Thread(
                target=self._run,
                name="upstox-market-stream",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Request shutdown and close the active socket if one exists."""
        self._stop.set()

        with self._lock:
            streamer = self._streamer

        if streamer is not None:
            try:
                streamer.disconnect()
            except Exception:
                # The socket may already have closed; shutdown remains valid.
                pass

        with self._lock:
            if self._state not in {"disabled", "not_configured"}:
                self._state = "stopped"

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            freshness, age = self._freshness_locked()
            return {
                "type": "quotes",
                "provider": "Upstox Market Data Feed V3",
                "mode": "websocket_ltpc",
                "connection": self._state,
                "feed_health": freshness,
                "tick_age_seconds": age,
                "sequence": self._sequence,
                "fetched_at": self._updated_at,
                "quotes": list(self._quotes.values()),
                "error": self._error,
                "diagnostics": {
                    **self._diagnostics,
                    "last_message_top_level_keys": list(
                        self._diagnostics["last_message_top_level_keys"]
                    ),
                    "last_feed_fields": list(self._diagnostics["last_feed_fields"]),
                    "last_instrument_keys_sample": list(
                        self._diagnostics["last_instrument_keys_sample"]
                    ),
                },
            }

    @staticmethod
    def _handshake_status(error: Any) -> int | None:
        """Extract an HTTP status from websocket-client handshake errors."""
        status = getattr(error, "status_code", None)
        if status in (401, 403):
            return int(status)

        match = re.search(r"Handshake status\s+(401|403)\b", str(error))
        return int(match.group(1)) if match else None

    def _run(self) -> None:
        """Run one socket at a time; this worker alone controls reconnection."""
        attempt = 0

        while not self._stop.is_set() and not self._fatal.is_set():
            streamer: Any = None
            token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()

            with self._lock:
                self._diagnostics["connection_attempts"] += 1

            try:
                if not token:
                    raise UpstoxAuthorizationError(
                        "UPSTOX_ACCESS_TOKEN is not configured."
                    )

                import upstox_client
                import websocket
                from upstox_client.feeder.market_data_feeder_v3 import (
                    MarketDataFeederV3,
                )

                config = upstox_client.Configuration()
                config.access_token = token
                client = upstox_client.ApiClient(config)

                mapping = _instrument_map()
                keys = list(
                    dict.fromkeys(
                        info["instrument_key"]
                        for info in mapping.values()
                        if info.get("instrument_key")
                    )
                )
                if not keys:
                    raise RuntimeError(
                        "No Upstox instruments are configured for streaming."
                    )

                if self._stop.is_set():
                    break

                manager = self
                with self._lock:
                    self._diagnostics["subscription_key_count"] = len(keys)

                class AuthorizedMarketDataFeederV3(MarketDataFeederV3):
                    """SDK feeder using a fresh V3-authorized URL per socket."""

                    def connect(self) -> None:
                        if (
                            self.ws is not None
                            and self.ws.sock is not None
                            and self.ws.sock.connected
                        ):
                            return

                        access_token = (
                            self.api_client.configuration.access_token
                        )
                        authorized_url = _get_authorized_feed_url(
                            access_token
                        )
                        with manager._lock:
                            manager._diagnostics["authorization_successes"] += 1

                        def record_then_decode(ws: Any, payload: Any) -> None:
                            manager._record_raw_message(payload)
                            self.on_message(ws, payload)

                        self.ws = websocket.WebSocketApp(
                            authorized_url,
                            on_open=self.on_open,
                            on_message=record_then_decode,
                            on_error=self.on_error,
                            on_close=self.on_close,
                        )

                        # Intentionally synchronous. The manager's worker
                        # remains here until this socket closes.
                        self.ws.run_forever(
                            sslopt={
                                "cert_reqs": ssl.CERT_REQUIRED,
                                "check_hostname": True,
                            }
                        )

                class AuthorizedMarketDataStreamerV3(
                    upstox_client.MarketDataStreamerV3
                ):
                    """Use the custom feeder but retain SDK decoding/events."""

                    def connect(self) -> None:
                        self.feeder = AuthorizedMarketDataFeederV3(
                            api_client=self.api_client,
                            instrumentKeys=self.instrumentKeys,
                            mode=self.mode,
                            on_open=self.handle_open,
                            on_message=self.handle_message,
                            on_error=self.handle_error,
                            on_close=self.handle_close,
                        )
                        self.feeder.connect()

                streamer = AuthorizedMarketDataStreamerV3(
                    client,
                    instrumentKeys=keys,
                    mode="ltpc",
                )

                # Avoid competing SDK and manager reconnect loops.
                streamer.auto_reconnect(False)

                with self._lock:
                    if self._stop.is_set():
                        break
                    self._streamer = streamer
                    self._state = "connecting"
                    self._error = None

                def on_open(*_args: Any) -> None:
                    nonlocal attempt
                    attempt = 0
                    with self._lock:
                        self._state = "connected"
                        self._error = None
                        self._diagnostics["socket_open_events"] += 1
                        self._diagnostics["subscription_event_at"] = (
                            self._diagnostic_timestamp()
                        )

                def on_message(message: Any) -> None:
                    self._consume(message, mapping)

                def on_error(error: Any) -> None:
                    status_code = self._handshake_status(error)
                    if status_code in (401, 403):
                        self._fatal.set()

                    message = str(error)
                    if token:
                        message = message.replace(token, "[redacted]")

                    with self._lock:
                        self._state = (
                            "error" if self._fatal.is_set() else "reconnecting"
                        )
                        self._error = message[:300]
                        self._diagnostics["errors_received"] += 1
                        self._diagnostics["last_error_at"] = (
                            self._diagnostic_timestamp()
                        )

                def on_close(*args: Any) -> None:
                    if self._stop.is_set() or self._fatal.is_set():
                        return

                    message = (
                        str(args[1])
                        if len(args) > 1 and args[1] is not None
                        else "Upstox stream disconnected."
                    )
                    if token:
                        message = message.replace(token, "[redacted]")

                    with self._lock:
                        self._state = "reconnecting"
                        self._error = message[:300]
                        self._diagnostics["close_events"] += 1

                streamer.on("open", on_open)
                streamer.on("message", on_message)
                streamer.on("error", on_error)
                streamer.on("close", on_close)

                # Blocks in run_forever until the WebSocket closes.
                streamer.connect()

                if not self._stop.is_set() and not self._fatal.is_set():
                    with self._lock:
                        self._state = "reconnecting"
                        self._error = (
                            "Upstox connection ended; retrying."
                        )

            except UpstoxAuthorizationError as exc:
                self._fatal.set()
                with self._lock:
                    self._state = "error"
                    self._error = str(exc)[:300]

            except Exception as exc:
                message = str(exc)
                if token:
                    message = message.replace(token, "[redacted]")

                with self._lock:
                    self._diagnostics["errors_received"] += 1
                    self._diagnostics["last_error_at"] = (
                        self._diagnostic_timestamp()
                    )
                    if not self._stop.is_set() and not self._fatal.is_set():
                        self._state = "reconnecting"
                        self._error = (
                            f"Upstox stream retry: "
                            f"{type(exc).__name__}: {message[:180]}"
                        )

            finally:
                if streamer is not None:
                    try:
                        streamer.disconnect()
                    except Exception:
                        pass

                with self._lock:
                    if self._streamer is streamer:
                        self._streamer = None

            if self._stop.is_set() or self._fatal.is_set():
                break

            delay = min(30, 2 ** min(attempt, 5))
            attempt += 1
            self._stop.wait(delay)

        with self._lock:
            self._streamer = None
            self._state = "error" if self._fatal.is_set() else "stopped"

    def _consume(
        self,
        message: Any,
        mapping: dict[str, dict[str, str]],
    ) -> None:
        """Convert decoded Upstox LTPC packets into the app quote format."""
        self._record_decoded_message_shape(message)
        if not isinstance(message, dict):
            return

        feeds = message.get("feeds") or {}
        if not isinstance(feeds, dict):
            return

        key_to_symbols: dict[str, list[str]] = {}
        for symbol, info in mapping.items():
            instrument_key = info.get("instrument_key")
            if instrument_key:
                key_to_symbols.setdefault(instrument_key, []).append(symbol)

        now = datetime.now(timezone.utc).isoformat()
        changed = False

        with self._lock:
            for instrument_key, feed in feeds.items():
                if not isinstance(feed, dict):
                    continue

                ltpc = feed.get("ltpc")
                if not isinstance(ltpc, dict):
                    full_feed = feed.get("fullFeed") or {}
                    market_ff = (
                        full_feed.get("marketFF")
                        or full_feed.get("indexFF")
                        or {}
                        if isinstance(full_feed, dict)
                        else {}
                    )
                    ltpc = (
                        market_ff.get("ltpc", {})
                        if isinstance(market_ff, dict)
                        else {}
                    )

                if (
                    not isinstance(ltpc, dict)
                    or not isinstance(ltpc.get("ltp"), (int, float))
                ):
                    continue

                with self._lock:
                    self._diagnostics["valid_ltpc_records"] += 1

                canonical = str(instrument_key).replace(":", "|")
                symbols = key_to_symbols.get(canonical, [])

                if not symbols:
                    symbols = [
                        symbol
                        for symbol, info in mapping.items()
                        if info.get("instrument_key") == canonical
                    ]

                if not symbols:
                    with self._lock:
                        self._diagnostics["unmatched_instrument_records"] += 1

                for symbol in symbols:
                    info = mapping[symbol]
                    last = float(ltpc["ltp"])
                    previous = ltpc.get("cp")

                    previous_number = (
                        float(previous)
                        if isinstance(previous, (int, float))
                        else None
                    )
                    change = (
                        round(last - previous_number, 4)
                        if previous_number is not None
                        else None
                    )
                    pct = (
                        round(change / previous_number * 100, 4)
                        if change is not None and previous_number
                        else None
                    )

                    self._quotes[symbol] = {
                        "symbol": symbol,
                        "name": info.get("name", symbol),
                        "instrument_key": info.get("instrument_key"),
                        "available": True,
                        "last_price": last,
                        "previous_close": previous_number,
                        "change": change,
                        "change_pct": pct,
                        "last_trade_quantity": ltpc.get("ltq"),
                        "last_trade_at": ltpc.get("ltt"),
                        "fetched_at": now,
                    }
                    changed = True

            if changed:
                self._updated_at = now
                self._sequence += 1
                self._state = "connected"
                self._error = None


stream_manager = UpstoxStreamManager()
