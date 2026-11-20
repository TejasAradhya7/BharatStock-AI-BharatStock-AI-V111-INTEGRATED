import numpy as np
import pandas as pd
from app.engine import indicators, sentiment_score

def sample_prices(n=100):
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = pd.Series(np.linspace(100, 150, n), index=idx)
    return pd.DataFrame({"Open":close-.5,"High":close+1,"Low":close-1,"Close":close,"Volume":1000}, index=idx)

def test_indicators_columns_and_ranges():
    out = indicators(sample_prices())
    assert {"SMA20","SMA50","EMA20","RSI","MACD","MACD_Signal","ATR","Volatility"} <= set(out.columns)
    assert out["RSI"].between(0,100).all()
    assert out["ATR"].dropna().ge(0).all()

def test_empty_history_rejected():
    try:
        indicators(pd.DataFrame(columns=["Open","High","Low","Close","Volume"]))
        assert False
    except ValueError:
        assert True

def test_sentiment_positive():
    score, label = sentiment_score("The company reports strong growth and record profit")
    assert score > 0 and label == "Positive"

def test_sentiment_negative():
    score, label = sentiment_score("The company reports fraud, losses and a major decline")
    assert score < 0 and label == "Negative"

def test_flat_market_has_neutral_rsi():
    idx = pd.date_range("2025-01-01", periods=80, freq="B")
    close = pd.Series(100.0, index=idx)
    prices = pd.DataFrame({"Open": close, "High": close, "Low": close,
                           "Close": close, "Volume": 1000}, index=idx)
    out = indicators(prices)
    assert (out["RSI"] == 50).all()


def test_uptrend_rsi_is_bounded_and_high():
    out = indicators(sample_prices(100))
    assert out["RSI"].between(0, 100).all()
    assert out["RSI"].iloc[-2] > 50
