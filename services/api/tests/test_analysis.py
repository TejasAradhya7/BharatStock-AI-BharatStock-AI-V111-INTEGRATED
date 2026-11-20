import numpy as np
import pandas as pd


def make_history(n=320):
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0.15, 1.2, n))
    target = (np.roll(close, -1) > close).astype(float)
    target[-1] = np.nan
    return pd.DataFrame({
        "RSI": rng.uniform(20, 80, n),
        "MACD": rng.normal(0, 1, n),
        "MACD_Signal": rng.normal(0, 1, n),
        "SMA20": close + rng.normal(0, 1, n),
        "SMA50": close + rng.normal(0, 2, n),
        "EMA20": close + rng.normal(0, 1, n),
        "ATR": rng.uniform(0.5, 3, n),
        "Volatility": rng.uniform(0.05, 0.5, n),
        "Target": target,
        "Close": close,
    })


def test_prediction_reports_baseline_and_chronological_holdout_metrics(monkeypatch):
    import app.analysis as analysis
    frame = make_history()
    monkeypatch.setattr(analysis, "fetch_history", lambda symbol, period: frame)
    result = analysis.predict("RELIANCE.NS", include_walk_forward=True)
    assert result["symbol"] == "RELIANCE.NS"
    assert result["predicted_direction"] in {"UP", "DOWN", "INSUFFICIENT_DATA"}
    assert 0 <= result["test_accuracy"] <= 1
    assert 0 <= result["majority_baseline_accuracy"] <= 1
    assert result["test_observations"] > 0
    assert result["up_probability"] is None or 0 <= result["up_probability"] <= 1
    assert len(result["feature_importance"]) == 8
    assert result["feature_importance"][0]["importance"] >= result["feature_importance"][-1]["importance"]
    assert abs(sum(item["importance"] for item in result["feature_importance"]) - 1.0) < 1e-6
    assert "majority-class baseline" in result["explanation"]
    holdout = result["holdout_model_comparison"]
    assert holdout["test_observations"] == result["test_observations"]
    assert holdout["random_forest_accuracy"] is None or 0 <= holdout["random_forest_accuracy"] <= 1
    assert 0 <= holdout["current_model_accuracy"] <= 1
    assert holdout["winner"] in {"RANDOM_FOREST_ON_THIS_HOLDOUT", "CURRENT_ENSEMBLE_ON_THIS_HOLDOUT", "TIE_OR_UNAVAILABLE"}
    assert holdout["independence_status"] == "previously_inspected_not_fresh_confirmatory_holdout"
    assert result["walk_forward"]["evaluation_scope"] == "pre-holdout model-selection data only"
    assert result["model_validation_status"] in {
        "INSUFFICIENT_VALIDATION", "WEAK_BELOW_BASELINE",
        "NO_CLEAR_EDGE", "PROMISING_NOT_PROVEN",
    }
    gap = result["walk_forward_accuracy_gap_vs_baseline"]
    assert gap is None or -1.0 <= gap <= 1.0
    if result["model_validation_status"] == "WEAK_BELOW_BASELINE":
        assert result["signal_quality"] == "LOW_VALIDATION_SUPPORT"
    assert result["walk_forward"]["folds"][-1]["test_end_index"] < int(len(frame[frame["Target"].notna()]) * 0.8) + 2
    candidates = {item["candidate"] for item in result["walk_forward"]["paired_candidate_comparisons"]}
    assert {"Random Forest", "Extra Trees", "Logistic Regression", "HistGradientBoosting"}.issubset(candidates)


def test_prediction_returns_insufficient_data_for_short_history(monkeypatch):
    import app.analysis as analysis
    frame = make_history(60)
    monkeypatch.setattr(analysis, "fetch_history", lambda symbol, period: frame)
    result = analysis.predict("TEST.NS")
    assert result["predicted_direction"] == "INSUFFICIENT_DATA"
    assert result["test_accuracy"] is None
    assert result["feature_importance"] == []


def test_walk_forward_evaluation_uses_expanding_chronological_folds():
    import app.analysis as analysis
    frame = make_history(320)
    features = ["RSI", "MACD", "MACD_Signal", "SMA20", "SMA50", "EMA20", "ATR", "Volatility"]
    result = analysis.walk_forward_evaluation(frame, features, folds=5)
    assert len(result["folds"]) == 5
    assert result["folds"][0]["train_observations"] < result["folds"][1]["train_observations"]
    assert result["folds"][1]["train_observations"] < result["folds"][2]["train_observations"]
    assert all(f["purged_boundary_observations"] == 1 for f in result["folds"])
    assert all(f["train_observations"] < f["test_start_index"] for f in result["folds"])
    assert "label-boundary purge" in result["method"]
    assert result["observations"] == sum(f["test_observations"] for f in result["folds"])
    assert 0 <= result["mean_accuracy"] <= 1
    assert 0 <= result["mean_baseline_accuracy"] <= 1
    assert "no shuffle" in result["method"]
    assert "moving-block bootstrap" in result["method"]
    paired = result["paired_model_comparison"]
    assert "moving_block_bootstrap_95pct_ci" in paired
    assert paired["same_unseen_folds"] == 5
    assert paired["rf_fold_wins"] + paired["current_model_fold_wins"] + paired["ties"] == 5
    assert paired["verdict"] in {"INSUFFICIENT_EVALUATION", "CANDIDATE_PROMISING_NOT_PROVEN", "CURRENT_ENSEMBLE_PROMISING_NOT_PROVEN", "NO_CLEAR_WINNER"}
    candidates = {item["candidate"] for item in result["paired_candidate_comparisons"]}
    assert {"Random Forest", "Extra Trees", "Logistic Regression", "HistGradientBoosting"}.issubset(candidates)
    assert all("moving_block_bootstrap_95pct_ci" in item for item in result["paired_candidate_comparisons"])


def test_walk_forward_evaluation_reports_insufficient_data():
    import app.analysis as analysis
    frame = make_history(100)
    features = ["RSI", "MACD", "MACD_Signal", "SMA20", "SMA50", "EMA20", "ATR", "Volatility"]
    result = analysis.walk_forward_evaluation(frame, features, folds=5)
    assert result["folds"] == []
    assert result["mean_accuracy"] is None


def test_v88_model_comparison_reports_class_aware_and_probability_metrics():
    import app.analysis as analysis
    frame = make_history(320)
    features = ["RSI", "MACD", "MACD_Signal", "SMA20", "SMA50", "EMA20", "ATR", "Volatility"]
    result = analysis.walk_forward_evaluation(frame, features, folds=5)
    candidates = {item["model"]: item for item in result["model_comparison"]}
    for name in ("Random Forest", "Extra Trees", "Logistic Regression", "HistGradientBoosting"):
        item = candidates[name]
        assert item["folds_evaluated"] == 5
        assert item["mean_balanced_accuracy"] is None or 0 <= item["mean_balanced_accuracy"] <= 1
        assert item["mean_precision_up"] is None or 0 <= item["mean_precision_up"] <= 1
        assert item["mean_brier_score"] is None or 0 <= item["mean_brier_score"] <= 1
        assert item["mean_log_loss"] is None or item["mean_log_loss"] >= 0
    assert "target_definition" in result
    assert "metric_guidance" in result


def test_v89_evaluation_audit_rejects_target_leakage_and_malformed_labels():
    import app.analysis as analysis
    frame = make_history(180)
    leaked = analysis.walk_forward_evaluation(frame, ["RSI", "future_return"], folds=3)
    assert leaked["evaluation_audit"]["status"] == "failed"
    assert leaked["paired_model_comparison"]["verdict"] == "INVALID_EVALUATION_INPUTS"

    bad_labels = frame.copy()
    bad_labels.loc[10, "Target"] = 2
    invalid = analysis.walk_forward_evaluation(
        bad_labels,
        ["RSI", "MACD", "MACD_Signal", "SMA20", "SMA50", "EMA20", "ATR", "Volatility"],
        folds=3,
    )
    assert invalid["evaluation_audit"]["status"] == "failed"
    assert invalid["paired_model_comparison"]["verdict"] == "INVALID_TARGET_LABELS"


def test_v89_reports_probability_metrics_for_ensemble_and_baseline_metrics():
    import app.analysis as analysis
    frame = make_history(240)
    features = ["RSI", "MACD", "MACD_Signal", "SMA20", "SMA50", "EMA20", "ATR", "Volatility"]
    result = analysis.walk_forward_evaluation(frame, features, folds=3)
    models = {item["model"]: item for item in result["model_comparison"]}
    ensemble = models["RF + Extra Trees ensemble"]
    baseline = models["Majority-class baseline"]
    assert ensemble["mean_precision_up"] is not None
    assert ensemble["mean_brier_score"] is not None
    assert ensemble["mean_log_loss"] is not None
    assert baseline["mean_balanced_accuracy"] is not None
    assert baseline["mean_precision_up"] is not None
    assert result["evaluation_audit"]["status"] == "passed"
    assert result["evaluation_audit"]["folds_use_same_test_rows"] is True


def test_model_selection_is_conservative_and_never_auto_promotes_production_model():
    import app.analysis as analysis
    frame = make_history(320)
    features = ["RSI", "MACD", "MACD_Signal", "SMA20", "SMA50", "EMA20", "ATR", "Volatility"]
    result = analysis.walk_forward_evaluation(frame, features, folds=5)
    recommendation = result["selection_recommendation"]
    assert recommendation["status"] in {
        "CANDIDATE_SHORTLISTED_REQUIRES_FUTURE_CONFIRMATION",
        "NO_CANDIDATE_CLEARED_BASELINE_GATE",
    }
    assert recommendation["production_model_changed"] is False
    assert recommendation["minimum_accuracy_edge_over_baseline"] == 0.01
    assert recommendation["minimum_folds"] == 5
    if recommendation["candidate"] is None:
        assert recommendation["status"] == "NO_CANDIDATE_CLEARED_BASELINE_GATE"
    else:
        candidate = next(item for item in result["model_comparison"] if item["model"] == recommendation["candidate"])
        baseline = next(item for item in result["model_comparison"] if item["model"] == "Majority-class baseline")
        assert candidate["mean_accuracy"] >= baseline["mean_accuracy"] + 0.01
        assert candidate["mean_balanced_accuracy"] >= 0.50
        assert candidate["folds_evaluated"] >= 5


def test_model_registry_persists_and_reuses_matching_artifact(tmp_path, monkeypatch):
    import app.model_registry as registry
    monkeypatch.setenv("BHARATSTOCK_MODEL_DIR", str(tmp_path))
    frame = make_history(240)
    close = pd.Series(frame["Close"])
    frame["MACD_pct"] = frame["MACD"] / close
    frame["MACD_Signal_pct"] = frame["MACD_Signal"] / close
    frame["SMA20_gap"] = close / frame["SMA20"] - 1
    frame["SMA50_gap"] = close / frame["SMA50"] - 1
    frame["EMA20_gap"] = close / frame["EMA20"] - 1
    frame["ATR_pct"] = frame["ATR"] / close
    frame["Return_5"] = close.pct_change(5)
    features = ["RSI", "MACD_pct", "MACD_Signal_pct", "SMA20_gap", "SMA50_gap", "EMA20_gap", "ATR_pct", "Return_5"]
    model1, meta1 = registry.load_or_train("TEST.NS", frame, features)
    model2, meta2 = registry.load_or_train("TEST.NS", frame, features)
    assert meta1["artifact_status"] == "trained_and_saved"
    assert meta2["artifact_status"] == "loaded"
    assert meta1["training_fingerprint"] == meta2["training_fingerprint"]
    assert list(model1.classes_) == list(model2.classes_)
    frame.loc[10, "RSI"] += 0.5
    _, meta3 = registry.load_or_train("TEST.NS", frame, features)
    assert meta3["artifact_status"] == "trained_and_saved"
