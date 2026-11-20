"""Controlled feature ablation for BharatStock AI intraday research.

Run inside the API container:
    python -m app.feature_ablation

Uses real Upstox 30-minute candles and PostgreSQL news_events.
Does not modify or enable the production prediction system.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, brier_score_loss,
    f1_score, log_loss, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .database import SessionLocal
from .models import NewsEvent
from .real_world import (
    align_news_features,
    build_intraday_features,
    fetch_upstox_historical,
    _expected_calibration_error,
    _non_overlapping_long_flat_backtest,
    _select_threshold_from_validation,
)

INSTRUMENT_KEY = "NSE_EQ|INE002A01018"  # RELIANCE
SYMBOL = "RELIANCE"
INTERVAL_MINUTES = 30
FOLDS = 3
COST_BPS_PER_SIDE = 10.0
HORIZON_BARS = 3

TECHNICAL = [
    "ret_1", "ret_2", "ret_3", "ret_6", "volatility_12",
    "sma_gap_5", "sma_gap_20", "ema_gap_8", "ema_gap_21",
    "range_pct", "body_pct", "close_location", "volume_ratio",
]
NEWS = [
    "news_event_count_24h",
    "news_sentiment_24h",
    "news_relevance_24h",
]
FEATURE_SETS = {
    "A_technical_only": TECHNICAL,
    "B_technical_plus_news": TECHNICAL + NEWS,
    "C_technical_news_plus_availability": TECHNICAL + NEWS + ["news_available"],
}


def model_factories():
    return {
        "Random Forest": lambda: RandomForestClassifier(
            n_estimators=160, max_depth=7, min_samples_leaf=4,
            class_weight="balanced_subsample", random_state=42, n_jobs=-1,
        ),
        "HistGradientBoosting": lambda: HistGradientBoostingClassifier(
            max_iter=100, learning_rate=0.05, max_leaf_nodes=15,
            l2_regularization=1.0, random_state=43,
        ),
        "Logistic Regression": lambda: make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=44),
        ),
    }


def fit_probability_model(factory, train, columns):
    y_train = train["Target"].astype(int)
    base = factory()
    if len(train) >= 80 and y_train.nunique() == 2:
        model = CalibratedClassifierCV(
            base, method="sigmoid", cv=TimeSeriesSplit(n_splits=3, gap=4)
        )
    else:
        model = base
    model.fit(train[columns], y_train)
    return model


def positive_probabilities(model, frame, columns):
    if not hasattr(model, "predict_proba"):
        raise RuntimeError("Selected estimator does not provide predict_proba.")
    classes = list(model.classes_)
    raw = np.asarray(model.predict_proba(frame[columns]), dtype=float)
    if 1 not in classes:
        return np.zeros(len(frame), dtype=float)
    return np.clip(raw[:, classes.index(1)], 1e-6, 1.0 - 1e-6)


def main():
    print("Fetching genuine Upstox V3 historical candles...")
    fetched = fetch_upstox_historical(
        instrument_key=INSTRUMENT_KEY,
        interval=INTERVAL_MINUTES,
    )
    candles = pd.DataFrame(fetched["candles"])
    if candles.empty:
        raise RuntimeError("Upstox returned no candles; stopping without synthetic data.")

    db = SessionLocal()
    try:
        latest_candle = pd.to_datetime(candles["timestamp"], utc=True).max()
        events = (
            db.query(NewsEvent)
            .filter(
                NewsEvent.symbol == INSTRUMENT_KEY,
                NewsEvent.available_at <= latest_candle.to_pydatetime(),
                ~NewsEvent.source_url.like("https://example.com/article-test-%"),
            )
            .order_by(NewsEvent.available_at.asc())
            .all()
        )
        news_payload = [
            {
                "available_at": event.available_at,
                "sentiment_score": event.sentiment_score,
                "relevance_score": event.relevance_score,
            }
            for event in events
        ]
    finally:
        db.close()

    print(f"Candles fetched: {len(candles)}")
    print(f"Matching news records available by latest candle: {len(news_payload)}")

    aligned = align_news_features(candles, news_payload)
    features = build_intraday_features(aligned)
    features["news_available"] = (
        pd.to_numeric(features["news_event_count_24h"], errors="coerce").fillna(0) > 0
    ).astype(int)

    # One common row set for all feature groups. This prevents differences in
    # observations or fold boundaries from being mistaken for feature gains.
    all_columns = TECHNICAL + NEWS + ["news_available"]
    missing = [column for column in all_columns if column not in features.columns]
    if missing:
        raise RuntimeError(f"Missing expected features: {missing}")

    clean = (
        features.replace([np.inf, -np.inf], np.nan)
        .dropna(subset=all_columns + ["Target", "target_return_3", "timestamp"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    n = len(clean)
    initial = max(40, int(n * 0.5))
    remaining = n - initial
    if remaining < FOLDS * 5:
        raise RuntimeError(
            f"Insufficient common observations ({n}) for {FOLDS} chronological folds."
        )

    fold_sizes = np.full(FOLDS, remaining // FOLDS, dtype=int)
    fold_sizes[:remaining % FOLDS] += 1

    print(f"Common usable observations: {n}")
    print(f"Rows with news available in trailing 24h: "
          f"{int((clean['news_event_count_24h'] > 0).sum())} "
          f"({(clean['news_event_count_24h'] > 0).mean():.2%})")
    print(f"Date range: {clean['timestamp'].iloc[0]} to {clean['timestamp'].iloc[-1]}")

    records = []
    fold_records = []
    factories = model_factories()
    cursor = initial

    for fold_no, size in enumerate(fold_sizes, start=1):
        # Match production benchmark's expanding split and 4-row purge.
        train = clean.iloc[:max(0, cursor - 4)].copy()
        test = clean.iloc[cursor:cursor + int(size)].copy()
        cursor += int(size)
        if train.empty or test.empty:
            continue

        fold_info = {
            "fold": fold_no,
            "train_rows": len(train),
            "test_rows": len(test),
            "test_start": test["timestamp"].iloc[0].isoformat(),
            "test_end": test["timestamp"].iloc[-1].isoformat(),
            "test_positive_rate": float(test["Target"].mean()),
        }

        for set_name, columns in FEATURE_SETS.items():
            for model_name, factory in factories.items():
                y_train = train["Target"].astype(int)
                y_test = test["Target"].astype(int)
                if y_train.nunique() < 2:
                    print(f"Skipping {set_name}/{model_name}/fold {fold_no}: "
                          "training fold contains one class.")
                    continue

                # Select threshold only on a purged chronological validation slice.
                validation_size = max(12, int(len(train) * 0.20))
                split_idx = len(train) - validation_size - 4
                threshold_selection = {
                    "status": "insufficient_validation_data",
                    "selected_threshold": None,
                    "selection_data": "validation_only",
                }
                selected_threshold = 1.0

                if split_idx >= 40:
                    threshold_train = train.iloc[:split_idx].copy()
                    validation = train.iloc[split_idx + 4:].copy()
                    if len(validation) >= 12 and threshold_train["Target"].nunique() == 2:
                        threshold_model = fit_probability_model(
                            factory, threshold_train, columns
                        )
                        validation_probs = positive_probabilities(
                            threshold_model, validation, columns
                        )
                        threshold_selection = _select_threshold_from_validation(
                            validation,
                            validation_probs,
                            cost_bps=COST_BPS_PER_SIDE,
                            horizon_bars=HORIZON_BARS,
                            min_trades=5,
                        )
                        if threshold_selection["status"] == "selected_on_validation":
                            selected_threshold = float(
                                threshold_selection["selected_threshold"]
                            )

                model = fit_probability_model(factory, train, columns)
                probs = positive_probabilities(model, test, columns)
                predictions = np.asarray(model.predict(test[columns]), dtype=int)

                metrics = {
                    "feature_set": set_name,
                    "model": model_name,
                    "fold": fold_no,
                    "feature_count": len(columns),
                    "train_observations": len(train),
                    "test_observations": len(test),
                    "test_start": test["timestamp"].iloc[0].isoformat(),
                    "test_end": test["timestamp"].iloc[-1].isoformat(),
                    "accuracy": float(accuracy_score(y_test, predictions)),
                    "balanced_accuracy": (
                        float(balanced_accuracy_score(y_test, predictions))
                        if y_test.nunique() > 1 else None
                    ),
                    "precision": float(precision_score(y_test, predictions, zero_division=0)),
                    "recall": float(recall_score(y_test, predictions, zero_division=0)),
                    "f1": float(f1_score(y_test, predictions, zero_division=0)),
                    "roc_auc": (
                        float(roc_auc_score(y_test, probs))
                        if y_test.nunique() > 1 else None
                    ),
                    "brier_score": float(brier_score_loss(y_test, probs)),
                    "log_loss": float(log_loss(y_test, probs, labels=[0, 1])),
                    "ece": _expected_calibration_error(y_test, probs),
                    "test_positive_rate": float(y_test.mean()),
                    "prediction_positive_rate": float(predictions.mean()),
                    "probability_mean": float(probs.mean()),
                    "probability_fraction_ge_060": float((probs >= 0.60).mean()),
                    "threshold_status": threshold_selection["status"],
                    "selected_threshold": selected_threshold,
                    "threshold_selection": threshold_selection,
                    **_non_overlapping_long_flat_backtest(
                        test, probs,
                        cost_bps=COST_BPS_PER_SIDE,
                        threshold=selected_threshold,
                        horizon_bars=HORIZON_BARS,
                    ),
                }
                records.append(metrics)
                print(
                    f"Fold {fold_no} | {set_name} | {model_name} | "
                    f"BA={metrics['balanced_accuracy']} | "
                    f"AUC={metrics['roc_auc']} | Brier={metrics['brier_score']:.4f}"
                )

        fold_records.append(fold_info)

    if not records:
        raise RuntimeError("No model/fold completed; no result files were written.")

    results = pd.DataFrame(records)
    numeric_metrics = [
        "accuracy", "balanced_accuracy", "roc_auc", "brier_score",
        "log_loss", "ece", "prediction_positive_rate", "probability_mean",
        "net_return_pct", "gross_benchmark_return_pct", "max_drawdown",
    ]
    summary = (
        results.groupby(["feature_set", "model"], dropna=False)[numeric_metrics + ["trades"]]
        .mean(numeric_only=True)
        .reset_index()
    )
    trade_totals = (
        results.groupby(["feature_set", "model"])["trades"]
        .sum().rename("total_test_trades").reset_index()
    )
    summary = summary.merge(trade_totals, on=["feature_set", "model"], how="left")

    output_dir = Path.cwd() / "research_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    csv_path = output_dir / f"bharatstock-reliance-feature-ablation-{stamp}.csv"
    summary_path = output_dir / f"bharatstock-reliance-feature-ablation-summary-{stamp}.csv"
    json_path = output_dir / f"bharatstock-reliance-feature-ablation-{stamp}.json"

    results.to_csv(csv_path, index=False)
    summary.to_csv(summary_path, index=False)

    payload = {
        "status": "completed",
        "symbol": SYMBOL,
        "instrument_key": INSTRUMENT_KEY,
        "provider": fetched["provider"],
        "interval_minutes": INTERVAL_MINUTES,
        "from_date": fetched["from_date"],
        "to_date": fetched["to_date"],
        "fetched_at": fetched["fetched_at"],
        "candles_fetched": len(candles),
        "news_records_available_by_latest_candle": len(news_payload),
        "common_usable_observations": n,
        "rows_with_trailing_24h_news": int((clean["news_event_count_24h"] > 0).sum()),
        "news_row_coverage_fraction": float((clean["news_event_count_24h"] > 0).mean()),
        "folds": fold_records,
        "feature_sets": FEATURE_SETS,
        "method": (
            "Same common observations, expanding chronological folds, 4-row purge, "
            "same target, same models, train-only calibration and validation-only "
            "threshold selection across all feature sets."
        ),
        "cost_assumption": {
            "one_way_bps": COST_BPS_PER_SIDE,
            "round_trip_bps": 2 * COST_BPS_PER_SIDE,
            "note": "Cost proxy only; not a complete Indian transaction-cost model."
        },
        "summary": summary.replace({np.nan: None}).to_dict(orient="records"),
        "fold_results": results.replace({np.nan: None}).to_dict(orient="records"),
        "limitations": [
            "This is a single-stock research ablation, not proof of generalization.",
            "News features are based on stored records and the project's keyword sentiment baseline.",
            "A missing historical news archive means older candles may have neutral news features.",
            "Backtest costs are an assumption and do not model all brokerage, taxes, spread, impact or slippage.",
            "No orders are placed and this script does not change production model behavior."
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print("\n=== FEATURE ABLATION SUMMARY ===")
    print(summary.to_string(index=False))
    print(f"\nDetailed fold CSV: {csv_path}")
    print(f"Summary CSV:       {summary_path}")
    print(f"Full JSON:         {json_path}")


if __name__ == "__main__":
    main()
