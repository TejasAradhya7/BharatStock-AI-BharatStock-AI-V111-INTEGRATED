import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.market import fetch_history


BASELINE = [
    "RSI",
    "MACD_pct",
    "MACD_Signal_pct",
    "SMA20_gap",
    "SMA50_gap",
    "EMA20_gap",
    "ATR_pct",
    "Return_5",
]

FEATURE_GROUPS = {
    "baseline": [],
    "momentum": [
        "Return_1",
        "Return_10",
        "Return_20",
    ],
    "volume": [
        "Relative_Volume",
        "Volume_Change",
    ],
    "volatility": [
        "Volatility_10",
        "Volatility_20",
        "Range_pct",
    ],
    "trend": [
        "SMA20_SMA50",
        "EMA20_SMA20",
        "Close_SMA50",
    ],
}

FEATURE_GROUPS["combined"] = [
    name
    for group in ("momentum", "volume", "volatility", "trend")
    for name in FEATURE_GROUPS[group]
]


def build_research_frame(df):
    data = df.copy()

    required = {"Open", "High", "Low", "Close", "Volume", "Target"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Market data is missing columns: {sorted(missing)}")

    close = pd.to_numeric(data["Close"], errors="coerce").replace(0, np.nan)
    high = pd.to_numeric(data["High"], errors="coerce")
    low = pd.to_numeric(data["Low"], errors="coerce")
    volume = pd.to_numeric(data["Volume"], errors="coerce")

    data["MACD_pct"] = pd.to_numeric(data["MACD"], errors="coerce") / close
    data["MACD_Signal_pct"] = (
        pd.to_numeric(data["MACD_Signal"], errors="coerce") / close
    )
    data["SMA20_gap"] = close / pd.to_numeric(data["SMA20"], errors="coerce") - 1
    data["SMA50_gap"] = close / pd.to_numeric(data["SMA50"], errors="coerce") - 1
    data["EMA20_gap"] = close / pd.to_numeric(data["EMA20"], errors="coerce") - 1
    data["ATR_pct"] = pd.to_numeric(data["ATR"], errors="coerce") / close
    data["Return_5"] = close.pct_change(5)

    # Additional features use only current and historical observations.
    data["Return_1"] = close.pct_change(1)
    data["Return_10"] = close.pct_change(10)
    data["Return_20"] = close.pct_change(20)

    volume_mean = volume.rolling(20).mean().replace(0, np.nan)
    data["Relative_Volume"] = volume / volume_mean
    data["Volume_Change"] = volume.pct_change()

    daily_return = close.pct_change()
    data["Volatility_10"] = daily_return.rolling(10).std() * np.sqrt(252)
    data["Volatility_20"] = daily_return.rolling(20).std() * np.sqrt(252)
    data["Range_pct"] = (high - low) / close

    data["SMA20_SMA50"] = (
        pd.to_numeric(data["SMA20"], errors="coerce")
        / pd.to_numeric(data["SMA50"], errors="coerce")
        - 1
    )
    data["EMA20_SMA20"] = (
        pd.to_numeric(data["EMA20"], errors="coerce")
        / pd.to_numeric(data["SMA20"], errors="coerce")
        - 1
    )
    data["Close_SMA50"] = close / pd.to_numeric(data["SMA50"], errors="coerce") - 1

    return data.replace([np.inf, -np.inf], np.nan)


def make_models():
    return {
        "logistic_regression": lambda: make_pipeline(
            StandardScaler(),
            LogisticRegression(
                max_iter=1500,
                class_weight="balanced",
                random_state=45,
            ),
        ),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            min_samples_leaf=5,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),
        "extra_trees": lambda: ExtraTreesClassifier(
            n_estimators=120,
            max_depth=8,
            min_samples_leaf=5,
            max_features="sqrt",
            class_weight="balanced",
            random_state=43,
            n_jobs=-1,
        ),
    }


def evaluate_fold(y_train, y_test, probabilities):
    predictions = (probabilities >= 0.5).astype(int)
    majority_class = int(y_train.mean() >= 0.5)
    majority_predictions = np.full(len(y_test), majority_class)

    return {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(
            balanced_accuracy_score(y_test, predictions)
        ),
        "brier_score": float(brier_score_loss(y_test, probabilities)),
        "log_loss": float(
            log_loss(y_test, np.column_stack([1 - probabilities, probabilities]),
                     labels=[0, 1])
        ),
        "majority_accuracy": float(
            accuracy_score(y_test, majority_predictions)
        ),
    }


def run_experiment(symbol, folds):
    print(f"Loading 5-year daily history for {symbol}...")
    raw = fetch_history(symbol, "5y")

    if raw is None or raw.empty:
        raise RuntimeError("No market history returned by fetch_history().")

    data = build_research_frame(raw)

    # Use one common sample for every feature set and model.
    all_features = sorted(set(BASELINE).union(
        *(set(v) for v in FEATURE_GROUPS.values())
    ))
    required_columns = all_features + ["Target", "Close"]
    data = data[required_columns].dropna().copy()

    data["Target"] = pd.to_numeric(data["Target"], errors="coerce")
    data = data[data["Target"].isin([0, 1])].copy()
    data["Target"] = data["Target"].astype(int)

    if len(data) < max(150, folds * 20):
        raise RuntimeError(
            f"Not enough clean observations ({len(data)}) for {folds} folds."
        )

    splitter = TimeSeriesSplit(n_splits=folds)
    split_indices = list(splitter.split(data))

    model_factories = make_models()
    results = []

    print(f"Clean observations: {len(data)}")
    print(f"Date range: {data.index.min()} to {data.index.max()}")
    print(f"Chronological folds: {folds}")
    print("One final training observation is purged at every fold boundary.")

    for feature_set, extra_features in FEATURE_GROUPS.items():
        selected_features = BASELINE + extra_features

        for model_name, model_factory in model_factories.items():
            fold_results = []

            for fold_number, (train_indices, test_indices) in enumerate(
                split_indices, start=1
            ):
                # Purge the last training row because its next-session target
                # can overlap the first test observation.
                train_indices = train_indices[:-1]

                if len(train_indices) == 0:
                    continue

                train = data.iloc[train_indices]
                test = data.iloc[test_indices]

                model = model_factory()
                model.fit(train[selected_features], train["Target"])

                probabilities = model.predict_proba(
                    test[selected_features]
                )[:, 1]

                metrics = evaluate_fold(
                    train["Target"].to_numpy(),
                    test["Target"].to_numpy(),
                    probabilities,
                )
                metrics["fold"] = fold_number
                metrics["train_rows"] = len(train)
                metrics["test_rows"] = len(test)
                fold_results.append(metrics)

            if not fold_results:
                continue

            metric_names = [
                "accuracy",
                "balanced_accuracy",
                "brier_score",
                "log_loss",
                "majority_accuracy",
            ]
            averages = {
                name: float(np.mean([fold[name] for fold in fold_results]))
                for name in metric_names
            }

            results.append({
                "feature_set": feature_set,
                "model": model_name,
                "feature_count": len(selected_features),
                "features": selected_features,
                "folds": fold_results,
                "mean": averages,
                "accuracy_minus_majority": (
                    averages["accuracy"] - averages["majority_accuracy"]
                ),
            })

            print(
                f"{feature_set:12s} | {model_name:20s} | "
                f"accuracy={averages['accuracy']:.4f} | "
                f"balanced={averages['balanced_accuracy']:.4f} | "
                f"majority={averages['majority_accuracy']:.4f} | "
                f"Brier={averages['brier_score']:.4f}"
            )

    results.sort(
        key=lambda item: (
            item["mean"]["balanced_accuracy"],
            item["accuracy_minus_majority"],
            -item["mean"]["brier_score"],
        ),
        reverse=True,
    )

    output = {
        "symbol": symbol,
        "period": "5y",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "validation": "expanding chronological TimeSeriesSplit",
            "fold_count": folds,
            "purge_rows": 1,
            "common_sample_for_all_experiments": True,
            "features_use_current_and_historical_data_only": True,
            "final_unknown_target_row_excluded": True,
            "production_model_modified": False,
            "warning": (
                "Research results are not proof of future profitability. "
                "Feature selection on these folds requires later independent "
                "out-of-sample confirmation."
            ),
        },
        "observations": len(data),
        "first_date": str(data.index.min()),
        "last_date": str(data.index.max()),
        "results": results,
    }

    output_dir = Path("/app/research_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{symbol.replace('^', '').replace('.', '_')}_feature_experiments.json"

    output_file.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("\n=== TOP EXPERIMENTS ===")
    for item in results[:10]:
        print(
            f"{item['feature_set']:12s} | {item['model']:20s} | "
            f"balanced_accuracy={item['mean']['balanced_accuracy']:.4f} | "
            f"accuracy={item['mean']['accuracy']:.4f} | "
            f"majority={item['mean']['majority_accuracy']:.4f}"
        )

    print(f"\nJSON report saved to: {output_file}")
    print("Production prediction code and model artifacts were not changed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="^NSEI")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    if args.folds < 3:
        parser.error("--folds must be at least 3")

    run_experiment(args.symbol, args.folds)
