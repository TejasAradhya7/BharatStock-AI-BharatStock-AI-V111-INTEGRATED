from datetime import datetime, timezone
import pandas as pd
import pytest
from app.real_world import (
    parse_iso_datetime,
    score_headline,
    build_intraday_features,
    walk_forward_intraday,
    _non_overlapping_long_flat_backtest,
    _select_threshold_from_validation,
    _select_classification_threshold,
    walk_forward_three_class_intraday,
)


def test_parse_iso_datetime_rejects_timezone_naive_values():
    with pytest.raises(ValueError, match="timezone"):
        parse_iso_datetime("2026-10-30T10:05:00")


def test_parse_iso_datetime_normalizes_to_utc():
    assert parse_iso_datetime("2026-10-30T10:05:00+05:30").utcoffset().total_seconds() == 0


def test_headline_sentiment_is_bounded_and_transparent():
    assert score_headline("Company reports strong growth and record profit") > 0
    assert score_headline("Company reports fraud probe and losses") < 0
    assert score_headline("company update") == 0


def test_intraday_features_are_sorted_and_do_not_use_future_bars_as_features():
    times = pd.date_range("2026-10-30 09:15", periods=60, freq="5min", tz="Asia/Kolkata")
    close = [100 + i * 0.1 for i in range(60)]
    candles = pd.DataFrame({"timestamp": list(times[::-1]), "open": close[::-1], "high": [x + .3 for x in close[::-1]],
                            "low": [x - .3 for x in close[::-1]], "close": close[::-1], "volume": [1000 + i for i in range(60)][::-1]})
    features = build_intraday_features(candles)
    assert features["timestamp"].is_monotonic_increasing
    assert features.iloc[20]["sma_gap_5"] == pytest.approx(close[20] / (sum(close[16:21]) / 5) - 1)
    assert features.iloc[-1]["target_return_3"] != features.iloc[-1]["target_return_3"]  # unknown future target
    expected_features = {
        "ret_12", "ret_24", "momentum_acceleration", "volatility_24",
        "sma_gap_50", "ema_gap_50", "time_of_day_sin", "time_of_day_cos",
        "weekday_sin", "weekday_cos", "gap_pct",
    }
    assert expected_features.issubset(features.columns)
    assert features["time_of_day_sin"].between(-1, 1).all()
    assert features["time_of_day_cos"].between(-1, 1).all()


def test_intraday_benchmark_fails_closed_with_small_sample():
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-10-30", periods=10, tz="UTC"), "Target": [0, 1] * 5,
                          "target_return_3": [0.01] * 10})
    result = walk_forward_intraday(frame)
    assert result["status"] == "insufficient_data"
    assert result["model_comparison"] == []


def test_intraday_walk_forward_benchmarks_only_supported_tabular_models():
    times = pd.date_range("2026-10-01 09:15", periods=240, freq="5min", tz="Asia/Kolkata")
    close = [100 + i * 0.02 + (0.3 if i % 7 < 4 else -0.2) for i in range(240)]
    candles = pd.DataFrame({"timestamp": times, "open": close, "high": [v + .25 for v in close],
                            "low": [v - .25 for v in close], "close": close,
                            "volume": [1000 + (i % 20) * 50 for i in range(240)]})
    engineered = build_intraday_features(candles)
    result = walk_forward_intraday(engineered, folds=3, cost_bps=10)
    assert result["status"] == "evaluated"
    assert result["observations"] > 50
    assert {"Random Forest baseline", "HistGradientBoosting", "Logistic Regression"}.issubset({m["model"] for m in result["model_comparison"]})
    assert result["three_class_evaluation"]["trading_enabled"] is False
    assert result["three_class_evaluation"]["class_labels"] == {"0": "DOWN", "1": "NO_TRADE", "2": "UP"}
    tabular_fold = next(f for f in result["folds"] if "Random Forest baseline" in f)
    cm = tabular_fold["Random Forest baseline"]["confusion_matrix"]
    assert len(cm) == 2 and all(len(row) == 2 for row in cm)
    assert sum(sum(row) for row in cm) == tabular_fold["test_observations"]
    assert "No model is selected automatically" in " ".join(result["limitations"])

def test_backtest_threshold_is_inclusive_and_costs_are_applied():
    test = pd.DataFrame({
        "close": [100.0, 101.0, 103.0, 104.0, 105.0,
                  106.0, 108.0, 109.0, 110.0, 111.0]
    })
    probabilities = [0.60] * len(test)

    result = _non_overlapping_long_flat_backtest(
        test,
        probabilities,
        cost_bps=10,
        threshold=0.60,
        horizon_bars=3,
    )

    assert result["status"] == "ok"
    assert result["signal_threshold"] == pytest.approx(0.60)
    assert result["trades"] == 2
    assert result["round_trip_cost_bps"] == pytest.approx(20.0)
    assert result["net_return_pct"] < result["gross_benchmark_return_pct"]


def test_backtest_does_not_trade_below_threshold():
    test = pd.DataFrame({
        "close": [100.0 + i for i in range(10)]
    })
    probabilities = [0.59] * len(test)

    result = _non_overlapping_long_flat_backtest(
        test,
        probabilities,
        cost_bps=10,
        threshold=0.60,
        horizon_bars=3,
    )

    assert result["status"] == "ok"
    assert result["trades"] == 0
    assert result["net_return_pct"] == pytest.approx(0.0)


def test_backtest_rejects_invalid_threshold():
    test = pd.DataFrame({"close": [100.0 + i for i in range(10)]})

    with pytest.raises(ValueError, match="threshold"):
        _non_overlapping_long_flat_backtest(
            test,
            [0.5] * len(test),
            threshold=1.1,
        )


def test_backtest_rejects_probability_length_mismatch():
    test = pd.DataFrame({"close": [100.0 + i for i in range(10)]})

    with pytest.raises(ValueError, match="probabilities length"):
        _non_overlapping_long_flat_backtest(
            test,
            [0.5, 0.6],
        )


def test_threshold_selection_fails_closed_when_no_threshold_has_enough_trades():
    import pandas as pd
    import numpy as np
    from app.real_world import _select_threshold_from_validation

    validation = pd.DataFrame({
        "close": np.linspace(100.0, 110.0, 30)
    })
    probabilities = np.full(len(validation), 0.40)

    result = _select_threshold_from_validation(
        validation,
        probabilities,
        min_trades=5,
    )

    assert result["status"] == "no_eligible_threshold"
    assert result["selected_threshold"] is None
    assert result["selection_data"] == "validation_only"


def test_threshold_selection_rejects_probability_length_mismatch():
    import pandas as pd
    from app.real_world import _select_threshold_from_validation

    validation = pd.DataFrame({"close": [100.0, 101.0, 102.0, 103.0]})

    try:
        _select_threshold_from_validation(validation, [0.5, 0.6])
    except ValueError as exc:
        assert "length" in str(exc)
    else:
        raise AssertionError("Expected ValueError for mismatched lengths")


def test_threshold_selection_rejects_invalid_probabilities():
    import pandas as pd
    from app.real_world import _select_threshold_from_validation

    validation = pd.DataFrame({"close": [100.0, 101.0, 102.0, 103.0]})

    try:
        _select_threshold_from_validation(validation, [0.4, 0.5, float("nan"), 0.7])
    except ValueError as exc:
        assert "finite" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid probabilities")



def test_classification_threshold_is_selected_on_validation_for_balanced_accuracy():
    y = [0,  0, 0, 0, 1, 1, 1, 1]
    probabilities = [0.12, 0.22, 0.31, 0.42, 0.48, 0.58, 0.68, 0.78]
    result = _select_classification_threshold(y, probabilities)
    assert result["status"] == "selected_on_validation"
    assert result["selection_data"] == "validation_only"
    assert result["validation_balanced_accuracy"] == pytest.approx(1.0)
    assert 0.25 <= result["selected_threshold"] <= 0.75


def test_classification_threshold_uses_neutral_default_for_single_class_validation():
    result = _select_classification_threshold([1, 1, 1], [0.7, 0.8, 0.9])
    assert result["status"] == "single_class_validation_default"
    assert result["selected_threshold"] == pytest.approx(0.50)


def test_classification_threshold_rejects_invalid_probabilities():
    with pytest.raises(ValueError, match="finite"):
        _select_classification_threshold([0, 1], [0.2, float("nan")])



def test_three_class_target_uses_cost_aware_neutral_band():
    import numpy as np
    from app.real_world import build_intraday_features

    times = pd.date_range("2026-10-01 09:15", periods=100, freq="5min", tz="Asia/Kolkata")
    close = np.array([100.0])
    rng = np.random.default_rng(711)
    steps = rng.normal(0.0001, 0.004, size=99)
    close = np.concatenate([close, 100.0 * np.cumprod(1.0 + steps)])
    candles = pd.DataFrame({
        "timestamp": times,
        "open": close * (1.0 - rng.normal(0.0, 0.0005, size=100)),
        "high": close * 1.003,
        "low": close * 0.997,
        "close": close,
        "volume": rng.integers(1000, 5000, size=100),
    })
    features = build_intraday_features(candles)
    valid = features.dropna(subset=["target_return_3"])
    expected = np.select(
        [valid["target_return_3"] < -0.002, valid["target_return_3"] > 0.002],
        [0, 2], default=1,
    )
    assert np.array_equal(valid["Target_3class"].to_numpy(dtype=int), expected)
    assert set(valid["Target_3class"].unique()).issubset({0, 1, 2})


def test_three_class_walk_forward_reports_all_classes_and_keeps_trading_disabled():
    import numpy as np
    times = pd.date_range("2026-10-01 09:15", periods=360, freq="5min", tz="Asia/Kolkata")
    rng = np.random.default_rng(991)
    close = 100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.004, size=360))
    candles = pd.DataFrame({
        "timestamp": times,
        "open": close * (1.0 + rng.normal(0.0, 0.0005, size=360)),
        "high": close * 1.004,
        "low": close * 0.996,
        "close": close,
        "volume": rng.integers(1000, 5000, size=360),
    })
    features = build_intraday_features(candles)
    result = walk_forward_three_class_intraday(features, folds=3, cost_bps=10)
    assert result["status"] == "evaluated"
    assert result["class_labels"] == {"0": "DOWN", "1": "NO_TRADE", "2": "UP"}
    assert result["round_trip_cost_bps"] == pytest.approx(20.0)
    assert result["trading_enabled"] is False
    assert len(result["folds"]) == 3
    for fold in result["folds"]:
        assert set(fold["test_class_counts"]) == {"DOWN", "NO_TRADE", "UP"}
        for model_name in ("Random Forest", "HistGradientBoosting", "Logistic Regression"):
            model_result = fold[model_name]
            if model_result.get("status") == "evaluated":
                assert len(model_result["confusion_matrix"]) == 3
                assert all(len(row) == 3 for row in model_result["confusion_matrix"])


def test_three_class_rejects_negative_cost_assumption():
    with pytest.raises(ValueError, match="non-negative"):
        walk_forward_three_class_intraday(pd.DataFrame(), cost_bps=-1)
