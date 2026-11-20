
import pandas as pd

import app.market as market


def test_daily_periods_share_canonical_provider_snapshot(monkeypatch):
    calls = []

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, period, auto_adjust):
            calls.append((self.symbol, period, auto_adjust))

            dates = pd.date_range("2022-01-01", periods=1100, freq="D")
            return pd.DataFrame(
                {
                    "Open": range(100, 1200),
                    "High": range(101, 1201),
                    "Low": range(99, 1199),
                    "Close": range(100, 1200),
                    "Volume": [1000] * len(dates),
                },
                index=dates,
            )

    class FakeYahoo:
        Ticker = FakeTicker

    monkeypatch.setattr(market, "_history_cache", {})
    monkeypatch.setitem(__import__("sys").modules, "yfinance", FakeYahoo)

    one_year = market.fetch_daily_history("^NSEI", "1y")
    five_year = market.fetch_daily_history("^NSEI", "5y")

    assert len(one_year) < len(five_year)
    assert one_year["Close"].iloc[-1] == five_year["Close"].iloc[-1]
    assert len(calls) == 1
    assert calls[0] == ("^NSEI", "5y", True)


def test_cached_history_returns_independent_copies(monkeypatch):
    class FakeTicker:
        def history(self, period, auto_adjust):
            dates = pd.date_range("2026-01-01", periods=60, freq="D")
            return pd.DataFrame(
                {
                    "Open": [100.0] * 60,
                    "High": [105.0] * 60,
                    "Low": [95.0] * 60,
                    "Close": [102.0] * 60,
                    "Volume": [1000] * 60,
                },
                index=dates,
            )

    class FakeYahoo:
        Ticker = lambda symbol: FakeTicker()

    monkeypatch.setattr(market, "_history_cache", {})
    monkeypatch.setitem(__import__("sys").modules, "yfinance", FakeYahoo)

    first = market.fetch_daily_history("^NSEI", "5y")
    first.iloc[-1, first.columns.get_loc("Close")] = -999

    second = market.fetch_daily_history("^NSEI", "5y")

    assert second["Close"].iloc[-1] == 102.0
