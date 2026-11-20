
from __future__ import annotations

import re
import threading
import time

import pandas as pd

from .engine import indicators


# Shared daily OHLCV cache.
# Cache raw provider data, not model predictions or calculated indicators.
_CACHE_TTL_SECONDS = 30
_history_cache: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}
_cache_lock = threading.Lock()


def validate_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol or len(symbol) > 24 or not re.fullmatch(r"[A-Z0-9.^=_-]+", symbol):
        raise ValueError("Enter a valid ticker symbol, e.g. RELIANCE.NS or ^NSEI.")
    return symbol


def _load_provider_history(symbol: str, provider_period: str) -> pd.DataFrame:
    """Load and briefly cache raw daily OHLCV data from Yahoo Finance."""
    key = (symbol, provider_period)
    now = time.monotonic()

    with _cache_lock:
        cached = _history_cache.get(key)
        if cached is not None:
            cached_at, cached_frame = cached
            if now - cached_at < _CACHE_TTL_SECONDS:
                return cached_frame.copy(deep=True)

        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                "Market-data dependency missing. Install services/api/requirements.txt."
            ) from exc

        frame = yf.Ticker(symbol).history(
            period=provider_period,
            auto_adjust=True,
        )

        if frame is None or frame.empty:
            raise LookupError(
                f"No market history returned for {symbol}. "
                "Check the ticker or provider availability."
            )

        frame = frame.rename(columns={column: column.title() for column in frame.columns})
        columns = ["Open", "High", "Low", "Close", "Volume"]
        missing = set(columns) - set(frame.columns)

        if missing:
            raise ValueError(
                f"Provider response missing columns: {sorted(missing)}"
            )

        frame = frame[columns].dropna(
            subset=["Open", "High", "Low", "Close"]
        ).copy()

        frame.index = pd.to_datetime(frame.index)
        frame = frame.sort_index()

        if frame.empty:
            raise LookupError(f"No valid OHLC data returned for {symbol}.")

        _history_cache[key] = (time.monotonic(), frame.copy(deep=True))
        return frame.copy(deep=True)


def _slice_period(frame: pd.DataFrame, period: str) -> pd.DataFrame:
    """Select the requested trailing period from canonical daily history."""
    if frame.empty or period in {"5y", "max"}:
        return frame.copy(deep=True)

    latest = frame.index[-1]
    offsets = {
        "1mo": pd.DateOffset(months=1),
        "3mo": pd.DateOffset(months=3),
        "6mo": pd.DateOffset(months=6),
        "1y": pd.DateOffset(years=1),
        "2y": pd.DateOffset(years=2),
    }

    if period not in offsets:
        raise ValueError(f"Unsupported historical period: {period}")

    start = latest - offsets[period]
    return frame.loc[frame.index >= start].copy(deep=True)


def fetch_daily_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Return raw daily OHLCV bars.

    Periods up to five years share one canonical five-year provider snapshot.
    Maximum-history requests use a separate provider snapshot.
    """
    symbol = validate_symbol(symbol)

    allowed = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}
    if period not in allowed:
        raise ValueError(f"Unsupported historical period: {period}")

    provider_period = "max" if period == "max" else "5y"
    frame = _load_provider_history(symbol, provider_period)
    return _slice_period(frame, period)


def fetch_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Return historical OHLCV with technical indicators."""
    symbol = validate_symbol(symbol)

    allowed = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}
    if period not in allowed:
        raise ValueError(f"Unsupported historical period: {period}")

    provider_period = "max" if period == "max" else "5y"
    raw = _load_provider_history(symbol, provider_period)

    # Calculate indicators before slicing so short periods retain their
    # historical warm-up observations.
    calculated = indicators(raw.copy(deep=True))
    return _slice_period(calculated, period)


def clear_history_cache() -> None:
    """Clear cached provider history; useful for tests and diagnostics."""
    with _cache_lock:
        _history_cache.clear()
