from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, HistGradientBoostingClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, brier_score_loss, log_loss
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .market import fetch_history
from .model_registry import load_or_train

def walk_forward_evaluation(data: pd.DataFrame, features: list[str], folds: int = 5) -> dict:
    """Compare models on identical expanding-window chronological folds.

    The target at row t depends on Close[t+1], so the final training row before
    each test window is purged. A paired moving-block bootstrap summarizes
    uncertainty in per-observation RF-minus-ensemble accuracy differences.
    This is diagnostic evidence, not a guarantee of future performance.
    """
    # Audit the evaluation inputs before fitting any model. Reject target-derived
    # columns and malformed labels rather than silently producing misleading scores.
    if not features or len(features) != len(set(features)):
        return {"folds": [], "model_comparison": [],
                "paired_model_comparison": {"verdict": "INVALID_FEATURE_SPECIFICATION"},
                "mean_accuracy": None, "std_accuracy": None,
                "mean_balanced_accuracy": None, "mean_baseline_accuracy": None,
                "observations": 0, "evaluation_audit": {"status": "failed", "reason": "Feature list is empty or contains duplicates."},
                "method": "evaluation stopped before model fitting"}
    forbidden_tokens = ("target", "label", "future", "forward", "next_close", "lead_")
    suspicious = [name for name in features if any(token in name.lower() for token in forbidden_tokens)]
    missing_columns = [name for name in features + ["Target"] if name not in data.columns]
    if suspicious or missing_columns:
        reason = []
        if suspicious:
            reason.append(f"Potential target/future leakage columns: {suspicious}")
        if missing_columns:
            reason.append(f"Missing required columns: {missing_columns}")
        return {"folds": [], "model_comparison": [],
                "paired_model_comparison": {"verdict": "INVALID_EVALUATION_INPUTS"},
                "mean_accuracy": None, "std_accuracy": None,
                "mean_balanced_accuracy": None, "mean_baseline_accuracy": None,
                "observations": 0, "evaluation_audit": {"status": "failed", "reason": "; ".join(reason)},
                "method": "evaluation stopped before model fitting"}
    raw_target = pd.to_numeric(data["Target"], errors="coerce").dropna()
    invalid_labels = sorted(set(raw_target.unique().tolist()) - {0, 1, 0.0, 1.0})
    if invalid_labels:
        return {"folds": [], "model_comparison": [],
                "paired_model_comparison": {"verdict": "INVALID_TARGET_LABELS"},
                "mean_accuracy": None, "std_accuracy": None,
                "mean_balanced_accuracy": None, "mean_baseline_accuracy": None,
                "observations": 0, "evaluation_audit": {"status": "failed", "reason": f"Target must be binary 0/1; found {invalid_labels[:10]}"},
                "method": "evaluation stopped before model fitting"}
    clean = data[features + ["Target"]].replace([np.inf, -np.inf], np.nan).dropna()
    n = len(clean)
    folds = max(2, min(int(folds), 8))
    initial_train = max(80, int(n * 0.5))
    remaining = n - initial_train
    if remaining < folds * 10:
        return {"folds": [], "model_comparison": [],
                "paired_model_comparison": {"verdict": "INSUFFICIENT_DATA"},
                "mean_accuracy": None, "std_accuracy": None,
                "mean_balanced_accuracy": None, "mean_baseline_accuracy": None,
                "observations": 0,
                "evaluation_audit": {"status": "passed", "target_values": sorted(set(raw_target.astype(int).tolist())),
                                     "feature_count": len(features), "leakage_name_scan": "passed", "folds_use_same_test_rows": True},
                "method": "expanding-window walk-forward; no shuffle; one-row label-boundary purge"}

    sizes = np.full(folds, remaining // folds, dtype=int)
    sizes[:remaining % folds] += 1
    cursor = initial_train
    results = []
    candidate_factories = {
        "Random Forest": lambda: RandomForestClassifier(
            n_estimators=120, max_depth=8, min_samples_leaf=5, max_features="sqrt",
            class_weight="balanced_subsample", random_state=42, n_jobs=1),
        "Extra Trees": lambda: ExtraTreesClassifier(
            n_estimators=120, max_depth=8, min_samples_leaf=5, max_features="sqrt",
            class_weight="balanced", random_state=43, n_jobs=1),
        "HistGradientBoosting": lambda: HistGradientBoostingClassifier(
            max_iter=100, learning_rate=0.06, max_leaf_nodes=15, l2_regularization=1.0,
            random_state=44),
        "Logistic Regression": lambda: make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced", random_state=45)),
    }
    candidate_scores = {name: [] for name in candidate_factories}
    candidate_balanced_scores = {name: [] for name in candidate_factories}
    candidate_up_precision = {name: [] for name in candidate_factories}
    candidate_brier_scores = {name: [] for name in candidate_factories}
    candidate_log_losses = {name: [] for name in candidate_factories}
    # Keep row-aligned correctness outcomes for paired candidate-versus-ensemble
    # comparisons. Every candidate sees exactly the same chronological test rows.
    candidate_correct = {name: [] for name in candidate_factories}
    paired_ensemble_correct = []
    ensemble_balanced_scores = []
    ensemble_up_precision = []
    ensemble_brier_scores = []
    ensemble_log_losses = []
    baseline_balanced_scores = []
    baseline_up_precision = []

    for index, size in enumerate(sizes, start=1):
        train_end = max(0, cursor - 1)
        train = clean.iloc[:train_end]
        test = clean.iloc[cursor:cursor + int(size)]
        if len(train) < 2 or test.empty:
            cursor += int(size)
            continue
        x_train, y_train = train[features], train["Target"].astype(int)
        x_test, y_test = test[features], test["Target"].astype(int)

        ensemble = _build_model()
        ensemble.fit(x_train, y_train)
        ensemble_pred = ensemble.predict(x_test)
        actual = y_test.to_numpy()
        ensemble_correct = (ensemble_pred == actual).astype(int)
        paired_ensemble_correct.extend(ensemble_correct.tolist())
        ensemble_balanced = float(balanced_accuracy_score(actual, ensemble_pred)) if len(np.unique(actual)) > 1 else None
        ensemble_precision = float(precision_score(actual, ensemble_pred, pos_label=1, zero_division=0))
        ensemble_classes = list(ensemble.classes_)
        ensemble_probabilities = ensemble.predict_proba(x_test)
        ensemble_up_probs = ensemble_probabilities[:, ensemble_classes.index(1)] if 1 in ensemble_classes else np.zeros(len(actual))
        ensemble_brier = float(brier_score_loss(actual, ensemble_up_probs)) if 1 in ensemble_classes else None
        ensemble_logloss = float(log_loss(actual, ensemble_probabilities, labels=ensemble_classes)) if len(ensemble_classes) > 1 else None
        ensemble_balanced_scores.append(ensemble_balanced)
        ensemble_up_precision.append(ensemble_precision)
        ensemble_brier_scores.append(ensemble_brier)
        ensemble_log_losses.append(ensemble_logloss)

        majority_class = int(y_train.value_counts().idxmax())
        baseline = np.full(len(test), majority_class, dtype=int)
        baseline_balanced_scores.append(float(balanced_accuracy_score(actual, baseline)) if len(np.unique(actual)) > 1 else None)
        baseline_up_precision.append(float(precision_score(actual, baseline, pos_label=1, zero_division=0)))
        fold_result = {
            "fold": index, "train_observations": int(len(train)),
            "test_start_index": int(cursor), "test_end_index": int(cursor + int(size)),
            "purged_boundary_observations": 1, "test_observations": int(len(test)),
            "accuracy": float(accuracy_score(y_test, ensemble_pred)),
            "balanced_accuracy": ensemble_balanced,
            "precision_up": ensemble_precision,
            "brier_score": ensemble_brier,
            "log_loss": ensemble_logloss,
            "baseline_accuracy": float(accuracy_score(y_test, baseline)),
            "baseline_balanced_accuracy": baseline_balanced_scores[-1],
            "baseline_precision_up": baseline_up_precision[-1],
        }

        # All candidates are evaluated on the exact same test rows. Report
        # class-aware and probability metrics as well as accuracy, because a
        # majority baseline can make raw accuracy misleading on imbalanced labels.
        for name, factory in candidate_factories.items():
            try:
                candidate = factory()
                candidate.fit(x_train, y_train)
                pred = candidate.predict(x_test)
                score = float(accuracy_score(y_test, pred))
                candidate_scores[name].append(score)
                candidate_balanced_scores[name].append(
                    float(balanced_accuracy_score(y_test, pred)) if len(np.unique(actual)) > 1 else None
                )
                candidate_up_precision[name].append(
                    float(precision_score(actual, pred, pos_label=1, zero_division=0))
                )
                classes = list(candidate.classes_) if hasattr(candidate, "classes_") else list(candidate[-1].classes_)
                probabilities = candidate.predict_proba(x_test)
                if 1 in classes:
                    up_probs = probabilities[:, classes.index(1)]
                    candidate_brier_scores[name].append(float(brier_score_loss(actual, up_probs)))
                    candidate_log_losses[name].append(float(log_loss(actual, probabilities, labels=classes)))
                else:
                    candidate_brier_scores[name].append(None)
                    candidate_log_losses[name].append(None)
                candidate_correct[name].extend((pred == actual).astype(int).tolist())
            except (ValueError, FloatingPointError, IndexError, AttributeError):
                candidate_scores[name].append(None)
                candidate_balanced_scores[name].append(None)
                candidate_up_precision[name].append(None)
                candidate_brier_scores[name].append(None)
                candidate_log_losses[name].append(None)
                candidate_correct[name].extend([None] * len(actual))
        results.append(fold_result)
        cursor += int(size)

    def valid_mean(values):
        valid = [v for v in values if v is not None and np.isfinite(v)]
        return float(np.mean(valid)) if valid else None

    ensemble_balanced = [x["balanced_accuracy"] for x in results]
    comparison = [{"model": "RF + Extra Trees ensemble",
                   "mean_accuracy": valid_mean([x["accuracy"] for x in results]),
                   "mean_balanced_accuracy": valid_mean(ensemble_balanced_scores),
                   "mean_precision_up": valid_mean(ensemble_up_precision),
                   "mean_brier_score": valid_mean(ensemble_brier_scores),
                   "mean_log_loss": valid_mean(ensemble_log_losses),
                   "folds_evaluated": len(results)}]
    for name, scores in candidate_scores.items():
        comparison.append({
            "model": name,
            "mean_accuracy": valid_mean(scores),
            "mean_balanced_accuracy": valid_mean(candidate_balanced_scores[name]),
            "mean_precision_up": valid_mean(candidate_up_precision[name]),
            "mean_brier_score": valid_mean(candidate_brier_scores[name]),
            "mean_log_loss": valid_mean(candidate_log_losses[name]),
            "folds_evaluated": sum(x is not None for x in scores),
        })
    baselines = [item["baseline_accuracy"] for item in results]
    comparison.append({"model": "Majority-class baseline",
                       "mean_accuracy": valid_mean(baselines),
                       "mean_balanced_accuracy": valid_mean(baseline_balanced_scores),
                       "mean_precision_up": valid_mean(baseline_up_precision),
                       "mean_brier_score": None,
                       "mean_log_loss": None,
                       "folds_evaluated": len(baselines)})
    comparison.sort(key=lambda x: x["mean_accuracy"] if x["mean_accuracy"] is not None else -1, reverse=True)

    # Conservative model-selection shortlist: require a minimum edge over the
    # fold-trained majority baseline and non-degenerate balanced accuracy.
    # This is never an automatic production-model promotion.
    baseline_mean = valid_mean(baselines)
    eligible_candidates = []
    for item in comparison:
        if item["model"] in {"RF + Extra Trees ensemble", "Majority-class baseline"}:
            continue
        accuracy_value = item.get("mean_accuracy")
        balanced_value = item.get("mean_balanced_accuracy")
        if (item.get("folds_evaluated", 0) >= 5 and accuracy_value is not None
                and baseline_mean is not None and balanced_value is not None
                and accuracy_value >= baseline_mean + 0.01
                and balanced_value >= 0.50):
            eligible_candidates.append(item)
    if eligible_candidates:
        eligible_candidates.sort(key=lambda item: (
            item["mean_accuracy"], item["mean_balanced_accuracy"],
            -(item["mean_brier_score"] if item["mean_brier_score"] is not None else 1.0)
        ), reverse=True)
        selection_recommendation = {
            "status": "CANDIDATE_SHORTLISTED_REQUIRES_FUTURE_CONFIRMATION",
            "candidate": eligible_candidates[0]["model"],
            "reason": "Candidate cleared the predeclared accuracy-over-baseline and balanced-accuracy gates. It is not promoted automatically.",
            "minimum_accuracy_edge_over_baseline": 0.01,
            "minimum_folds": 5,
            "production_model_changed": False,
        }
    else:
        selection_recommendation = {
            "status": "NO_CANDIDATE_CLEARED_BASELINE_GATE",
            "candidate": None,
            "reason": "No candidate beat the fold-trained majority baseline by at least 1 percentage point while reaching 0.50 mean balanced accuracy on at least five chronological folds.",
            "minimum_accuracy_edge_over_baseline": 0.01,
            "minimum_folds": 5,
            "production_model_changed": False,
        }

    # Paired moving-block bootstrap for every candidate against the ensemble.
    # Model-selection folds are expected to be strictly earlier than the final
    # holdout; predict() enforces this by passing only its pre-holdout training
    # portion into this function.
    def paired_summary(name: str, candidate_outcomes: list) -> dict:
        n_pairs = min(len(candidate_outcomes), len(paired_ensemble_correct))
        differences = []
        for candidate_value, ensemble_value in zip(candidate_outcomes[:n_pairs], paired_ensemble_correct[:n_pairs]):
            if candidate_value is not None:
                differences.append(float(candidate_value) - float(ensemble_value))
        diffs = np.asarray(differences, dtype=float)
        paired_n = len(diffs)
        mean_diff = float(diffs.mean()) if paired_n else None
        ci_low = ci_high = None
        block_len = max(2, int(round(paired_n ** (1 / 3)))) if paired_n else None
        if paired_n >= 30:
            rng = np.random.default_rng(20261103 + sum(ord(ch) for ch in name))
            starts_count = int(np.ceil(paired_n / block_len))
            boot_means = np.empty(1000, dtype=float)
            for b in range(len(boot_means)):
                starts = rng.integers(0, paired_n, size=starts_count)
                sample = np.concatenate([
                    diffs[np.arange(st, st + block_len) % paired_n] for st in starts
                ])[:paired_n]
                boot_means[b] = sample.mean()
            ci_low, ci_high = (float(np.quantile(boot_means, 0.025)),
                               float(np.quantile(boot_means, 0.975)))
        fold_scores = candidate_scores.get(name, [])
        comparable = [(r["accuracy"], score) for r, score in zip(results, fold_scores) if score is not None]
        candidate_wins = sum(candidate_score > ensemble_score + 1e-12 for ensemble_score, candidate_score in comparable)
        ensemble_wins = sum(ensemble_score > candidate_score + 1e-12 for ensemble_score, candidate_score in comparable)
        ties = len(comparable) - candidate_wins - ensemble_wins
        if len(comparable) < 5 or paired_n < 30:
            verdict = "INSUFFICIENT_EVALUATION"
        elif ci_low is not None and ci_low > 0 and mean_diff is not None and mean_diff > 0:
            verdict = "CANDIDATE_PROMISING_NOT_PROVEN"
        elif ci_high is not None and ci_high < 0 and mean_diff is not None and mean_diff < 0:
            verdict = "CURRENT_ENSEMBLE_PROMISING_NOT_PROVEN"
        else:
            verdict = "NO_CLEAR_WINNER"
        return {
            "candidate": name, "current_model": "RF + Extra Trees ensemble",
            "same_unseen_folds": len(comparable), "candidate_fold_wins": int(candidate_wins),
            "current_model_fold_wins": int(ensemble_wins), "ties": int(ties),
            "paired_observations": int(paired_n),
            "mean_accuracy_difference_candidate_minus_current": mean_diff,
            "moving_block_bootstrap_95pct_ci": {"lower": ci_low, "upper": ci_high,
                                                "block_length": block_len,
                                                "resamples": 1000 if paired_n >= 30 else 0},
            "verdict": verdict,
        }

    paired_candidate_comparisons = [
        paired_summary(name, outcomes) for name, outcomes in candidate_correct.items()
    ]
    rf_summary = next((item for item in paired_candidate_comparisons if item["candidate"] == "Random Forest"), None)
    paired_comparison = dict(rf_summary or {"candidate": "Random Forest", "verdict": "INSUFFICIENT_EVALUATION"})
    # Preserve the V86 API field names for existing dashboard clients.
    paired_comparison["rf_fold_wins"] = paired_comparison.pop("candidate_fold_wins", 0)
    paired_comparison["mean_accuracy_difference_rf_minus_current"] = paired_comparison.pop(
        "mean_accuracy_difference_candidate_minus_current", None)
    paired_comparison["interpretation"] = (
        "Paired chronological model-selection folds with moving-block bootstrap intervals. "
        "These folds must precede the final holdout; intervals quantify sampling uncertainty "
        "but do not guarantee future performance. A new future-period holdout is needed for "
        "independent confirmation after model selection."
    )
    accuracies = [item["accuracy"] for item in results]
    balanced = [item["balanced_accuracy"] for item in results if item["balanced_accuracy"] is not None]
    return {
        "folds": results, "model_comparison": comparison,
        "selection_recommendation": selection_recommendation,
        "paired_model_comparison": paired_comparison,
        "paired_candidate_comparisons": paired_candidate_comparisons,
        "mean_accuracy": valid_mean(accuracies),
        "std_accuracy": float(np.std(accuracies, ddof=1)) if len(accuracies) > 1 else (0.0 if accuracies else None),
        "mean_balanced_accuracy": valid_mean(balanced),
        "mean_baseline_accuracy": valid_mean(baselines),
        "observations": int(sum(item["test_observations"] for item in results)),
        "method": "pre-holdout expanding-window walk-forward; no shuffle; one-row label-boundary purge; identical chronological test rows for every candidate; paired moving-block bootstrap for each candidate versus ensemble; majority-class baseline trained per fold",
        "target_definition": "next-session close direction (Close[t+1] > Close[t]); final row without a future close is excluded",
        "evaluation_audit": {
            "status": "passed",
            "target_values": sorted(set(raw_target.astype(int).tolist())),
            "target_definition": "binary next-session direction; target=1 iff next close is greater than current close",
            "feature_count": len(features),
            "leakage_name_scan": "passed; no feature names contain target/label/future/forward/next_close/lead_ tokens",
            "folds_use_same_test_rows": True,
            "training_window_expands": True,
            "label_boundary_purge_rows": 1,
            "majority_baseline_fit_on_training_rows_only": True,
            "caveat": "Name scanning cannot prove absence of semantic leakage; feature construction must also be reviewed.",
        },
        "metric_guidance": {
            "accuracy": "fraction of correctly classified observations; compare with the fold-trained majority baseline",
            "balanced_accuracy": "mean recall across classes; null for a single-class test fold",
            "precision_up": "precision for predicted UP class; not a measure of profitability",
            "brier_score": "mean squared error of UP probabilities; lower is better",
            "log_loss": "probability scoring loss; lower is better",
            "probability_metrics_note": "Scores are uncalibrated model probabilities and must not be interpreted as investment success probabilities"
        },
    }


def _build_model():
    """Create a fresh ensemble for each training window; no future observations are used."""
    forest = RandomForestClassifier(
        n_estimators=300, max_depth=8, min_samples_leaf=5,
        max_features="sqrt", class_weight="balanced_subsample",
        random_state=42, n_jobs=1,
    )
    extra = ExtraTreesClassifier(
        n_estimators=250, max_depth=8, min_samples_leaf=5,
        max_features="sqrt", class_weight="balanced",
        random_state=43, n_jobs=1,
    )
    # Soft voting blends different tree learners; probabilities are model scores,
    # not calibrated probabilities of investment success.
    return VotingClassifier(
        estimators=[("random_forest", forest), ("extra_trees", extra)],
        voting="soft", weights=[1, 1], n_jobs=1,
    )


def predict(symbol: str, include_walk_forward: bool = False) -> dict:
    df = fetch_history(symbol, "5y").copy()
    # Price-level indicators (SMA20/SMA50/EMA20/ATR/MACD) scale with the
    # nominal price of a stock and can make a cross-regime model brittle.
    # Convert them to dimensionless ratios so the same learner can generalize
    # better across price levels and splits. Every feature uses data available
    # at or before that row; the target remains next-session direction.
    close = pd.to_numeric(df["Close"], errors="coerce").replace(0, np.nan)
    df["MACD_pct"] = df["MACD"] / close
    df["MACD_Signal_pct"] = df["MACD_Signal"] / close
    df["SMA20_gap"] = close / pd.to_numeric(df["SMA20"], errors="coerce") - 1.0
    df["SMA50_gap"] = close / pd.to_numeric(df["SMA50"], errors="coerce") - 1.0
    df["EMA20_gap"] = close / pd.to_numeric(df["EMA20"], errors="coerce") - 1.0
    df["ATR_pct"] = pd.to_numeric(df["ATR"], errors="coerce") / close
    # Short-horizon momentum is causal and adds information not represented by
    # RSI alone. Keep a fixed feature count for compatibility with the UI.
    df["Return_5"] = close.pct_change(5)
    features = ["RSI", "MACD_pct", "MACD_Signal_pct", "SMA20_gap", "SMA50_gap", "EMA20_gap", "ATR_pct", "Return_5"]
    data = df[features + ["Target", "Close"]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 120:
        return {"symbol": symbol.upper(), "latest_close": float(df["Close"].iloc[-1]),
                "predicted_direction": "INSUFFICIENT_DATA", "model": "RandomForest",
                "test_accuracy": None, "feature_importance": [], "walk_forward": {"folds": [], "mean_accuracy": None, "std_accuracy": None, "mean_balanced_accuracy": None, "mean_baseline_accuracy": None, "observations": 0, "method": "expanding-window walk-forward; no shuffle"}, "explanation": "Not enough clean historical observations to evaluate safely."}
    # Strict chronological split. Target is next-session direction; never random-shuffle time series.
    split = int(len(data) * .8)
    # Purge the final training row because its next-session label uses the first
    # test row's close. Keep the test window unchanged and strictly chronological.
    train, test = data.iloc[:max(0, split - 1)], data.iloc[split:]
    x_train, y_train = train[features], train["Target"].astype(int)
    x_test, y_test = test[features], test["Target"].astype(int)
    model = _build_model()
    model.fit(x_train, y_train)
    test_predictions = model.predict(x_test) if len(test) else np.array([], dtype=int)
    acc = float(accuracy_score(y_test, test_predictions)) if len(test) else None
    # Direct RF-vs-current-model comparison on the exact same untouched final
    # chronological holdout. Neither model is trained on these test labels.
    rf_holdout_accuracy = None
    if include_walk_forward:
        rf_holdout = RandomForestClassifier(
            n_estimators=120, max_depth=8, min_samples_leaf=5, max_features="sqrt",
            class_weight="balanced_subsample", random_state=42, n_jobs=1,
        )
        rf_holdout.fit(x_train, y_train)
        rf_holdout_predictions = rf_holdout.predict(x_test) if len(test) else np.array([], dtype=int)
        rf_holdout_accuracy = float(accuracy_score(y_test, rf_holdout_predictions)) if len(test) else None
    balanced_acc = float(balanced_accuracy_score(y_test, test_predictions)) if len(test) and y_test.nunique() > 1 else None
    # A majority-class baseline makes the model score easier to interpret than accuracy alone.
    baseline_class = int(y_train.value_counts().idxmax()) if len(y_train) else 0
    baseline_acc = float(accuracy_score(y_test, np.full(len(y_test), baseline_class, dtype=int))) if len(test) else None
    # The holdout metrics above are computed before this refit. For the live
    # prediction, train on every row whose next-session target is now observable.
    # The latest row itself has Target=NaN and is therefore excluded from `data`.
    model, artifact_metadata = load_or_train(symbol, data, features)
    latest = df[features].replace([np.inf, -np.inf], np.nan).dropna().tail(1)
    if latest.empty:
        direction = "INSUFFICIENT_DATA"
        up_probability = None
    else:
        predicted_class = int(model.predict(latest)[0])
        direction = "UP" if predicted_class == 1 else "DOWN"
        probabilities = model.predict_proba(latest)[0]
        classes = list(model.classes_)
        up_probability = float(probabilities[classes.index(1)]) if 1 in classes else 0.0
    # Model selection must not reuse the final 20% holdout. Use only the
    # pre-holdout portion for walk-forward candidate comparisons. The holdout
    # score remains diagnostic because earlier project versions already exposed it.
    if include_walk_forward:
        walk_forward = walk_forward_evaluation(train, features, folds=5)
        walk_forward["evaluation_scope"] = "pre-holdout model-selection data only"
    else:
        walk_forward = {
            "folds": [], "model_comparison": [],
            "mean_accuracy": None, "std_accuracy": None,
            "mean_balanced_accuracy": None, "mean_baseline_accuracy": None,
            "observations": 0,
            "method": "Skipped for interactive prediction latency; run the Research Lab for chronological walk-forward evaluation.",
            "evaluation_scope": "not_run_for_live_prediction",
        }
    walk_forward["final_holdout_note"] = (
        "The final 20% holdout is excluded from walk-forward model selection. "
        "Because this holdout was reported in earlier project versions, it is not a fresh untouched confirmatory set; use future observations for independent confirmation."
    )
    # VotingClassifier has no single native feature_importances_; average the
    # constituent tree importances so the UI can still explain model inputs.
    fitted_importances = [
        estimator.feature_importances_
        for estimator in model.estimators_
        if hasattr(estimator, "feature_importances_")
    ]
    mean_importance = np.mean(fitted_importances, axis=0) if fitted_importances else np.zeros(len(features))
    importances = sorted(
        ({"feature": name, "importance": float(value)} for name, value in zip(features, mean_importance)),
        key=lambda item: item["importance"], reverse=True,
    )
    # Model probability is descriptive, not a calibrated probability of investment success.
    # Crucially, do not label a high model score as a strong signal when historical
    # walk-forward performance is weaker than a simple training-only baseline.
    confidence = max(up_probability, 1.0 - up_probability) if up_probability is not None else None
    wf_accuracy = walk_forward.get("mean_accuracy")
    wf_baseline = walk_forward.get("mean_baseline_accuracy")
    wf_balanced = walk_forward.get("mean_balanced_accuracy")
    if wf_accuracy is None or wf_baseline is None or wf_balanced is None:
        model_validation_status = "INSUFFICIENT_VALIDATION"
    elif wf_accuracy < wf_baseline and wf_balanced < 0.5:
        model_validation_status = "WEAK_BELOW_BASELINE"
    elif wf_accuracy <= wf_baseline + 0.01 or wf_balanced <= 0.52:
        model_validation_status = "NO_CLEAR_EDGE"
    else:
        model_validation_status = "PROMISING_NOT_PROVEN"

    if model_validation_status == "WEAK_BELOW_BASELINE":
        signal_quality = "LOW_VALIDATION_SUPPORT"
    elif confidence is not None and confidence < 0.55:
        signal_quality = "LOW_CONFIDENCE"
    elif confidence is not None and confidence < 0.65:
        signal_quality = "WEAK"
    else:
        signal_quality = "MODEL_CONFIDENCE_ONLY"
    return {"symbol": symbol.upper(), "latest_close": float(df["Close"].iloc[-1]),
            "predicted_direction": direction, "model": artifact_metadata["model_name"],
            "model_version": artifact_metadata["model_version"],
            "model_artifact_status": artifact_metadata["artifact_status"],
            "model_trained_at": artifact_metadata["trained_at"],
            "model_training_rows": artifact_metadata["training_rows"],
            "model_feature_schema": artifact_metadata["features"],
            "confidence": confidence, "signal_quality": signal_quality,
            "model_validation_status": model_validation_status,
            "walk_forward_accuracy_gap_vs_baseline": (
                float(wf_accuracy - wf_baseline)
                if wf_accuracy is not None and wf_baseline is not None else None
            ),
            "accuracy_target_note": "80% directional accuracy is a research goal, not a guaranteed result. Compare models on chronological out-of-sample folds; this output is research-only.",
            "feature_importance": importances, "walk_forward": walk_forward,
            "test_accuracy": acc, "balanced_accuracy": balanced_acc,
            "majority_baseline_accuracy": baseline_acc, "test_observations": int(len(test)),
            "holdout_model_comparison": {
                "test_period": "final chronological 20% holdout",
                "test_observations": int(len(test)),
                "current_model": "RF + Extra Trees ensemble", "current_model_accuracy": acc,
                "random_forest_accuracy": rf_holdout_accuracy,
                "majority_baseline_accuracy": baseline_acc,
                "random_forest_minus_current": (rf_holdout_accuracy - acc) if rf_holdout_accuracy is not None and acc is not None else None,
                "winner": ("RANDOM_FOREST_ON_THIS_HOLDOUT" if rf_holdout_accuracy is not None and acc is not None and rf_holdout_accuracy > acc else "CURRENT_ENSEMBLE_ON_THIS_HOLDOUT" if rf_holdout_accuracy is not None and acc is not None and acc > rf_holdout_accuracy else "TIE_OR_UNAVAILABLE"),
                "independence_status": "previously_inspected_not_fresh_confirmatory_holdout",
                "warning": "This holdout was reported in earlier project versions, so treat it as diagnostic rather than fresh independent confirmation. Validate final choices on future observations."
            },
            "up_probability": up_probability,
            "explanation": "The versioned ensemble is loaded from a persisted artifact when its symbol, feature schema, and labelled-data fingerprint match; otherwise it is retrained and atomically saved. Price-level indicators are normalized into relative gaps/ratios, and five-session momentum is included. The model comparison evaluates several model families on chronological walk-forward folds. It does not learn from a prediction outcome until that outcome is observable in later market data. Accuracy near the majority-class baseline is weak evidence; no accuracy level is guaranteed. An 80–90% directional hit rate has not been demonstrated and cannot be promised. This is experimental research, not investment advice."}
