"""Upstox V3 LTP integration.

The access token is read only on the server. The frontend never receives it.
Quotes are current snapshots fetched from Upstox; a client can poll this endpoint
for a near-real-time dashboard. For tick-by-tick streaming, use the Upstox V3
WebSocket feed in a separate streaming worker.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

UPSTOX_LTP_URL = "https://api.upstox.com/v3/market-quote/ltp"
# Short per-process cache reduces duplicate upstream calls when many dashboards
# request the same watchlist at nearly the same time. Set TTL to 0 to disable.
_quote_cache: dict[tuple[str, ...], tuple[float, dict[str, Any]]] = {}
_quote_cache_lock = threading.Lock()


def _quote_cache_ttl() -> float:
    try:
        return max(0.0, min(30.0, float(os.getenv("UPSTOX_QUOTE_CACHE_SECONDS", "1"))))
    except (TypeError, ValueError):
        return 1.0


def clear_quote_cache() -> None:
    """Clear the in-process snapshot cache (primarily useful for tests)."""
    with _quote_cache_lock:
        _quote_cache.clear()
DEFAULT_INSTRUMENTS: dict[str, dict[str, str]] = {
    "^NSEI": {"name": "NIFTY 50", "instrument_key": "NSE_INDEX|Nifty 50", "exchange": "NSE"},
    "^BSESN": {"name": "SENSEX", "instrument_key": "BSE_INDEX|SENSEX", "exchange": "BSE"},
    "RELIANCE.NS": {"name": "Reliance Industries", "instrument_key": "NSE_EQ|INE002A01018", "exchange": "NSE"},
    "TCS.NS": {"name": "Tata Consultancy Services", "instrument_key": "NSE_EQ|INE467B01029", "exchange": "NSE"},
    "INFY.NS": {"name": "Infosys", "instrument_key": "NSE_EQ|INE009A01021", "exchange": "NSE"},
    "HDFCBANK.NS": {"name": "HDFC Bank", "instrument_key": "NSE_EQ|INE040A01034", "exchange": "NSE"},
    "ICICIBANK.NS": {"name": "ICICI Bank", "instrument_key": "NSE_EQ|INE090A01021", "exchange": "NSE"},
    "SBIN.NS": {"name": "State Bank of India", "instrument_key": "NSE_EQ|INE062A01020", "exchange": "NSE"},
    "ITC.NS": {"name": "ITC", "instrument_key": "NSE_EQ|INE154A01025", "exchange": "NSE"},
    "HINDUNILVR.NS": {"name": "Hindustan Unilever", "instrument_key": "NSE_EQ|INE030A01027", "exchange": "NSE"},
    "LT.NS": {"name": "Larsen & Toubro", "instrument_key": "NSE_EQ|INE018A01030", "exchange": "NSE"},
    "BHARTIARTL.NS": {"name": "Bharti Airtel", "instrument_key": "NSE_EQ|INE397D01024", "exchange": "NSE"},
    "AXISBANK.NS": {"name": "Axis Bank", "instrument_key": "NSE_EQ|INE238A01034", "exchange": "NSE"},
    "KOTAKBANK.NS": {"name": "Kotak Mahindra Bank", "instrument_key": "NSE_EQ|INE237A01028", "exchange": "NSE"},
    "MARUTI.NS": {"name": "Maruti Suzuki", "instrument_key": "NSE_EQ|INE585B01010", "exchange": "NSE"},
    "SUNPHARMA.NS": {"name": "Sun Pharmaceutical", "instrument_key": "NSE_EQ|INE044A01036", "exchange": "NSE"},
    "TATAMOTORS.NS": {"name": "Tata Motors", "instrument_key": "NSE_EQ|INE155A01022", "exchange": "NSE"},
}


def _instrument_map() -> dict[str, dict[str, str]]:
    """Allow users to override/add mappings using JSON in UPSTOX_INSTRUMENT_KEYS."""
    mapping = {key: value.copy() for key, value in DEFAULT_INSTRUMENTS.items()}
    raw = os.getenv("UPSTOX_INSTRUMENT_KEYS", "").strip()
    if raw:
        try:
            custom = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("UPSTOX_INSTRUMENT_KEYS must be valid JSON.") from exc
        if not isinstance(custom, dict):
            raise RuntimeError("UPSTOX_INSTRUMENT_KEYS must be a JSON object mapping symbols to instrument keys.")
        for symbol, item in custom.items():
            normalized = str(symbol).strip().upper()
            if isinstance(item, str):
                instrument_key, name = item.strip(), normalized
            elif isinstance(item, dict):
                instrument_key = str(item.get("instrument_key", "")).strip()
                name = str(item.get("name", normalized)).strip()
            else:
                continue
            if not normalized or not instrument_key or "|" not in instrument_key:
                raise RuntimeError(f"Invalid Upstox instrument mapping for {normalized or 'symbol'}.")
            mapping[normalized] = {"name": name, "instrument_key": instrument_key, "exchange": instrument_key.split("|", 1)[0]}
    return mapping


def normalize_symbols(raw: str | list[str]) -> list[str]:
    values = raw if isinstance(raw, list) else raw.split(",")
    symbols = list(dict.fromkeys(str(value).strip().upper() for value in values if str(value).strip()))
    if not symbols:
        raise ValueError("Provide at least one supported symbol.")
    if len(symbols) > 20:
        raise ValueError("Request up to 20 symbols per dashboard refresh.")
    mapping = _instrument_map()
    unknown = [symbol for symbol in symbols if symbol not in mapping]
    if unknown:
        raise ValueError("No Upstox instrument key configured for: " + ", ".join(unknown) + ". Add it to UPSTOX_INSTRUMENT_KEYS.")
    return symbols


def live_provider_status() -> dict[str, Any]:
    token_configured = bool(os.getenv("UPSTOX_ACCESS_TOKEN", "").strip())
    return {
        "provider": "Upstox V3 LTP",
        "configured": token_configured,
        "mode": "REST snapshot polling",
        "refresh_recommendation_seconds": 5,
        "supported_symbols": [
            {"symbol": symbol, "name": info["name"], "instrument_key": info["instrument_key"]}
            for symbol, info in _instrument_map().items()
        ],
        "note": "Quotes are fetched from Upstox when requested. The access token stays on the backend.",
    }


def get_live_quotes(symbols: list[str]) -> dict[str, Any]:
    token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Upstox is not configured. Set UPSTOX_ACCESS_TOKEN in the backend environment and restart the API.")
    # Normalize ordering so the same watchlist in a different order can reuse a
    # cached provider response; cache is isolated by instrument list, not token.
    cache_key = tuple(sorted(set(symbols)))
    ttl = _quote_cache_ttl()
    now = time.monotonic()
    if ttl > 0:
        with _quote_cache_lock:
            cached = _quote_cache.get(cache_key)
            if cached and now - cached[0] < ttl:
                response = dict(cached[1])
                response["cache"] = {"hit": True, "ttl_seconds": ttl}
                response["note"] = "Snapshot reused briefly to reduce duplicate Upstox requests; prices may be up to the configured cache TTL old. This is not tick-by-tick streaming."
                return response
    mapping = _instrument_map()
    keys = [mapping[symbol]["instrument_key"] for symbol in symbols]
    try:
        response = httpx.get(
            UPSTOX_LTP_URL,
            params={"instrument_key": ",".join(keys)},
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            timeout=8.0,
        )
    except httpx.TimeoutException as exc:
        raise RuntimeError("Upstox quote request timed out. Try again shortly.") from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Could not connect to Upstox. Check backend network access.") from exc
    if response.status_code in (401, 403):
        raise RuntimeError("Upstox rejected the access token. Generate a valid token and update UPSTOX_ACCESS_TOKEN.")
    if response.status_code == 429:
        raise RuntimeError("Upstox rate limit reached. Increase the dashboard refresh interval.")
    if response.status_code >= 400:
        raise RuntimeError(f"Upstox returned HTTP {response.status_code}. Check instrument keys and API access.")
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Upstox returned an unreadable quote response.") from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise RuntimeError("Upstox response did not contain quote data.")

    quotes: list[dict[str, Any]] = []
    for symbol in symbols:
        instrument_key = mapping[symbol]["instrument_key"]
        found = None
        # Upstox response map keys may use colon notation; match token if included.
        for quote in data.values():
            if not isinstance(quote, dict):
                continue
            token_value = str(quote.get("instrument_token", ""))
            if token_value == instrument_key:
                found = quote
                break
        if found is None:
            expected = instrument_key.replace("|", ":")
            found = data.get(expected)
        if found is None:
            # Single-instrument responses normally contain exactly one item.
            if len(symbols) == 1 and len(data) == 1:
                candidate = next(iter(data.values()))
                if isinstance(candidate, dict):
                    found = candidate
        if not isinstance(found, dict):
            quotes.append({"symbol": symbol, "name": mapping[symbol]["name"], "instrument_key": instrument_key, "available": False})
            continue
        last_price = found.get("last_price")
        previous_close = found.get("cp")
        change = None
        change_pct = None
        if isinstance(last_price, (int, float)) and isinstance(previous_close, (int, float)):
            change = round(float(last_price) - float(previous_close), 4)
            if previous_close:
                change_pct = round(change / float(previous_close) * 100, 4)
        quotes.append({
            "symbol": symbol,
            "name": mapping[symbol]["name"],
            "instrument_key": instrument_key,
            "available": isinstance(last_price, (int, float)),
            "last_price": last_price,
            "previous_close": previous_close,
            "change": change,
            "change_pct": change_pct,
            "volume": found.get("volume"),
            "last_trade_quantity": found.get("ltq"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    result = {
        "provider": "Upstox V3 LTP",
        "mode": "REST snapshot polling",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "quotes": quotes,
        "cache": {"hit": False, "ttl_seconds": ttl},
        "note": "Prices reflect the latest values returned by Upstox. This endpoint polls snapshots; it is not a tick-by-tick WebSocket stream.",
    }
    if ttl > 0:
        with _quote_cache_lock:
            _quote_cache[cache_key] = (time.monotonic(), result)
            # Keep memory bounded even if users request many different symbol sets.
            if len(_quote_cache) > 500:
                oldest_keys = sorted(_quote_cache, key=lambda key: _quote_cache[key][0])[:100]
                for old_key in oldest_keys:
                    _quote_cache.pop(old_key, None)
    return result
