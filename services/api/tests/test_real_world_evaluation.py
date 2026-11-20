import numpy as np
import pandas as pd
import pytest
from app.real_world import build_intraday_features, _non_overlapping_long_flat_backtest


def sample_candles(n=80):
    close = 100 + np.arange(n, dtype=float) * 0.2 + np.sin(np.arange(n) / 3)
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01 09:15", periods=n, freq="5min", tz="Asia/Kolkata"),
        "open": close - 0.1, "high": close + 0.5, "low": close - 0.5,
        "close": close, "volume": np.arange(n) + 1000,
    })


def test_target_uses_next_close_entry_and_three_bar_hold():
    candles = sample_candles()
    result = build_intraday_features(candles)
    # Signal row t, entry close[t+1], exit close[t+4].
    expected = candles["close"].iloc[4] / candles["close"].iloc[1] - 1
    assert result["target_return_3"].iloc[0] == pytest.approx(expected)
    assert result["Target"].iloc[0] == int(expected > 0)
    assert result["target_return_3"].tail(4).isna().all()


def test_backtest_compounds_and_matches_benchmark_with_non_overlapping_windows():
    test = pd.DataFrame({"close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]})
    probabilities = np.array([0.7] * len(test))
    result = _non_overlapping_long_flat_backtest(test, probabilities, cost_bps=0, threshold=0.6, horizon_bars=3)
    # Candidate t=0, t=3, and t=6; next-close entries and 3-bar holds are sequential.
    expected_strategy = (104 / 101) * (107 / 104) * (110 / 107) - 1
    expected_benchmark = expected_strategy
    assert result["non_overlapping_candidates"] == 3
    assert result["trades"] == 3
    assert result["net_return_pct"] == pytest.approx(expected_strategy * 100)
    assert result["gross_benchmark_return_pct"] == pytest.approx(expected_benchmark * 100)
    assert result["max_drawdown"] == pytest.approx(0.0)


def test_backtest_deducts_round_trip_cost_only_for_active_trades():
    test = pd.DataFrame({"close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]})
    probabilities = np.array([0.1] * len(test))
    result = _non_overlapping_long_flat_backtest(test, probabilities, cost_bps=10, threshold=0.6, horizon_bars=3)
    assert result["trades"] == 0
    assert result["net_return_pct"] == pytest.approx(0.0)
    assert result["gross_benchmark_return_pct"] > 0


def test_backtest_rejects_probability_length_mismatch():
    with pytest.raises(ValueError, match="length"):
        _non_overlapping_long_flat_backtest(pd.DataFrame({"close": [1, 2, 3]}), [0.5], horizon_bars=1)


def test_walk_forward_emits_classification_and_backtest_metrics():
    from app.real_world import walk_forward_intraday
    features = build_intraday_features(sample_candles(100))
    result = walk_forward_intraday(features, folds=2, cost_bps=10)
    assert result["status"] == "evaluated"
    assert result["folds"]
    first_model = next(k for k in result["folds"][0] if k not in {"fold", "train_observations", "test_observations", "test_start", "test_end"})
    metrics = result["folds"][0][first_model]
    assert "precision" in metrics and "recall" in metrics and "f1" in metrics and "roc_auc" in metrics
    assert "gross_benchmark_return_pct" in metrics and "max_drawdown" in metrics


def test_backtest_deducts_round_trip_cost_from_active_trades():
    test = pd.DataFrame({
        "close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    })
    probabilities = np.array([0.7] * len(test))

    result = _non_overlapping_long_flat_backtest(
        test,
        probabilities,
        cost_bps=10,
        threshold=0.6,
        horizon_bars=3,
    )

    gross_returns = np.array([
        104 / 101 - 1,
        107 / 104 - 1,
        110 / 107 - 1,
    ])
    expected_net = np.prod(1 + gross_returns - 0.002) - 1

    assert result["trades"] == 3
    assert result["round_trip_cost_bps"] == pytest.approx(20.0)
    assert result["net_return_pct"] == pytest.approx(expected_net * 100)


def test_backtest_fails_closed_when_all_candidate_probabilities_are_invalid():
    test = pd.DataFrame({
        "close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    })
    probabilities = np.array([np.nan] * len(test))

    result = _non_overlapping_long_flat_backtest(
        test,
        probabilities,
        cost_bps=10,
        threshold=0.6,
        horizon_bars=3,
    )

    assert result["status"] == "no_valid_candidates"
    assert result["trades"] == 0
    assert result["net_return_pct"] is None


def test_intraday_features_add_causal_ema_and_candle_features():
    candles = sample_candles(100)
    result = build_intraday_features(candles)
    for column in ("ema_gap_8", "ema_gap_21", "body_pct", "close_location"):
        assert column in result.columns
        assert result[column].iloc[30:].notna().all()
    changed = candles.copy()
    changed[["open", "high", "low", "close", "volume"]] = changed[["open", "high", "low", "close", "volume"]].astype(float)
    changed.loc[50:, ["open", "high", "low", "close", "volume"]] *= 1.5
    changed_features = build_intraday_features(changed)
    # Features at row 40 cannot depend on candles after row 40.
    for column in ("ema_gap_8", "ema_gap_21", "body_pct", "close_location"):
        assert result.loc[40, column] == pytest.approx(changed_features.loc[40, column])


def test_walk_forward_reports_train_only_baselines_and_class_diagnostics():
    from app.real_world import walk_forward_intraday
    features = build_intraday_features(sample_candles(160))
    result = walk_forward_intraday(features, folds=2, cost_bps=10)
    assert result["status"] == "evaluated"
    first = result["folds"][0]
    assert "Majority-class baseline" in first
    assert "Constant-probability baseline" in first
    assert first["class_diagnostics"]["train_positive_rate"] == pytest.approx(
        first["Majority-class baseline"]["training_positive_rate"]
    )
    assert "prediction_positive_rate" in first["Logistic Regression"]
    names = {item["model"] for item in result["model_comparison"]}
    assert "Majority-class baseline" in names
    assert "Constant-probability baseline" in names
