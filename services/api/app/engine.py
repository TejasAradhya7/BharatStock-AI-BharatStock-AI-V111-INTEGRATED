"""Preserved/testable market indicators and sentiment analysis."""
from __future__ import annotations
import numpy as np
import pandas as pd

def indicators(df: pd.DataFrame) -> pd.DataFrame:
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Price history is empty")
    x = df.copy().sort_index()
    c, h, l = x["Close"], x["High"], x["Low"]
    x["SMA20"] = c.rolling(20).mean()
    x["SMA50"] = c.rolling(50).mean()
    x["EMA20"] = c.ewm(span=20, adjust=False).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    # Explicitly handle edge cases: all gains => 100, all losses => 0,
    # and a flat series => neutral 50 (rather than incorrectly returning 0).
    rsi = rsi.where(loss.ne(0), 100.0)
    rsi = rsi.where(gain.ne(0), 0.0)
    flat = gain.eq(0) & loss.eq(0)
    rsi = rsi.where(~flat, 50.0)
    x["RSI"] = rsi.fillna(50).clip(0, 100)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    x["MACD"] = ema12 - ema26
    x["MACD_Signal"] = x["MACD"].ewm(span=9, adjust=False).mean()
    prev = c.shift(1)
    tr = pd.concat([h-l, (h-prev).abs(), (l-prev).abs()], axis=1).max(axis=1)
    x["ATR"] = tr.rolling(14).mean()
    x["Return"] = c.pct_change()
    x["Volatility"] = x["Return"].rolling(20).std() * np.sqrt(252)
    x["Target"] = (c.shift(-1) > c).astype(float)
    x.loc[x.index[-1], "Target"] = np.nan
    return x

def sentiment_score(text: str) -> tuple[float, str]:
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        score = SentimentIntensityAnalyzer().polarity_scores(text)["compound"]
    except ImportError:
        # Deterministic fallback for offline/unit-test environments; install requirements for VADER.
        positive = ["gain", "growth", "profit", "beats", "surge", "strong", "record", "upgrade", "rises", "positive", "bullish"]
        negative = ["loss", "losses", "fall", "drops", "weak", "fraud", "crash", "downgrade", "decline", "negative", "bearish"]
        words = text.lower()
        score = (sum(w in words for w in positive) - sum(w in words for w in negative)) / max(3, len(words.split()))
    label = "Positive" if score >= .05 else ("Negative" if score <= -.05 else "Neutral")
    return float(score), label
