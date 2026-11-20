"""BharatStock AI: five-stock leakage-aware intraday model evaluation V2.

Run inside the API container:
    python -m app.multi_stock_feature_ablation

This is a research/evaluation script. It does not alter production predictions
or place orders. It uses genuine Upstox V3 candles and point-in-time news.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score,
    brier_score_loss, confusion_matrix, f1_score, log_loss, matthews_corrcoef,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .database import SessionLocal
from .models import NewsEvent
from .real_world import (
    align_news_features, build_intraday_features, fetch_upstox_historical,
    fetch_upstox_intraday, _expected_calibration_error,
    _non_overlapping_long_flat_backtest, _select_threshold_from_validation,
)
from .feature_ablation import fit_probability_model, positive_probabilities

STOCKS = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "INFY": "NSE_EQ|INE009A01021",
    # Preserve the instrument key in the user's current project configuration.
    "SBIN": "NSE_EQ|INE062A01020",
    "ICICIBANK": "NSE_EQ|INE090A01021",
}
INTERVAL_MINUTES = 30
FOLDS = 3
COST_BPS_PER_SIDE = 10.0
HORIZON_BARS = 3
MIN_VALIDATION_TRADES = 5

TECHNICAL = [
    "ret_1", "ret_2", "ret_3", "ret_6", "volatility_12",
    "sma_gap_5", "sma_gap_20", "ema_gap_8", "ema_gap_21",
    "range_pct", "body_pct", "close_location", "volume_ratio",
]
NEWS = ["news_event_count_24h", "news_sentiment_24h", "news_relevance_24h"]


def model_factories():
    """Paired imbalance treatments: balanced and unweighted versions."""
    return {
        "RF_balanced": lambda: RandomForestClassifier(
            n_estimators=240, max_depth=7, min_samples_leaf=4,
            class_weight="balanced_subsample", random_state=42, n_jobs=-1,
        ),
        "RF_unweighted": lambda: RandomForestClassifier(
            n_estimators=240, max_depth=7, min_samples_leaf=4,
            class_weight=None, random_state=42, n_jobs=-1,
        ),
        "HGB_baseline": lambda: HistGradientBoostingClassifier(
            max_iter=120, learning_rate=0.05, max_leaf_nodes=15,
            l2_regularization=1.0, random_state=43,
        ),
        "LR_balanced": lambda: make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1500, class_weight="balanced", random_state=44),
        ),
        "LR_unweighted": lambda: make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1500, class_weight=None, random_state=44),
        ),
    }


def fit_model(factory, train: pd.DataFrame, columns: list[str]):
    """Fit using the project's chronological sigmoid-calibration helper."""
    # The existing helper uses TimeSeriesSplit(n_splits=3, gap=4) when possible.
    return fit_probability_model(factory, train, columns)


def confusion_metrics(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": (
            float(balanced_accuracy_score(y_true, y_pred))
            if len(np.unique(y_true)) > 1 else None
        ),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "prediction_positive_rate": float(np.mean(y_pred)),
    }


def pooled_confusion_metrics(group: pd.DataFrame) -> dict:
    tn = int(group["tn"].sum())
    fp = int(group["fp"].sum())
    fn = int(group["fn"].sum())
    tp = int(group["tp"].sum())
    total = tn + fp + fn + tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "pooled_tn": tn, "pooled_fp": fp, "pooled_fn": fn, "pooled_tp": tp,
        "pooled_observations": total,
        "pooled_accuracy": (tn + tp) / total if total else None,
        "pooled_balanced_accuracy": (
            (recall + specificity) / 2 if (tn + fp) and (tp + fn) else None
        ),
        "pooled_precision": precision,
        "pooled_recall": recall,
        "pooled_f1": f1,
    }


def prepare_stock(symbol: str, instrument_key: str):
    print(f"\n[{symbol}] Fetching Upstox V3 historical + intraday candles...")
    historical = fetch_upstox_historical(
        instrument_key=instrument_key, interval=INTERVAL_MINUTES
    )
    hist = pd.DataFrame(historical["candles"])
    if hist.empty:
        raise RuntimeError("Upstox returned no historical candles.")

    intraday = None
    live = pd.DataFrame()
    try:
        intraday = fetch_upstox_intraday(
            instrument_key=instrument_key, interval=INTERVAL_MINUTES
        )
        live = pd.DataFrame(intraday["candles"])
    except LookupError as exc:
        print(f"[{symbol}] Current-day intraday unavailable: {exc}")

    as_of = (
        pd.to_datetime(intraday["fetched_at"], utc=True)
        if intraday is not None else pd.Timestamp.now(tz="UTC")
    )
    candles = pd.concat([hist, live], ignore_index=True)
    candles["timestamp"] = pd.to_datetime(
        candles["timestamp"], utc=True, errors="coerce"
    )
    candles = (
        candles.dropna(subset=["timestamp"])
        .drop_duplicates("timestamp", keep="last")
        .sort_values("timestamp").reset_index(drop=True)
    )
    candle_end = candles["timestamp"] + pd.Timedelta(INTERVAL_MINUTES, unit="min")
    candles = candles.loc[candle_end <= as_of].copy().reset_index(drop=True)
    if candles.empty:
        raise RuntimeError("No completed candles available after filtering.")

    latest_close = candles["timestamp"].max() + pd.Timedelta(
        INTERVAL_MINUTES, unit="min"
    )
    db = SessionLocal()
    try:
        events = (
            db.query(NewsEvent)
            .filter(
                NewsEvent.symbol == instrument_key,
                NewsEvent.available_at <= latest_close.to_pydatetime(),
            )
            .order_by(NewsEvent.available_at.asc()).all()
        )
        payload = [{
            "available_at": e.available_at,
            "sentiment_score": e.sentiment_score,
            "relevance_score": e.relevance_score,
        } for e in events]
    finally:
        db.close()

    # Align each news observation to candle completion, not candle opening.
    original_ts = candles["timestamp"].copy()
    news_frame = candles.copy()
    news_frame["timestamp"] = (
        pd.to_datetime(news_frame["timestamp"], utc=True)
        + pd.Timedelta(INTERVAL_MINUTES, unit="min")
    )
    aligned = align_news_features(news_frame, payload)
    aligned["timestamp"] = original_ts.to_numpy()
    features = build_intraday_features(aligned)

    # Do not let a supervised target cross an overnight/session boundary or
    # bridge missing 30-minute bars.
    ts = pd.to_datetime(features["timestamp"], utc=True)
    session = ts.dt.tz_convert("Asia/Kolkata").dt.date
    valid = pd.Series(True, index=features.index)
    for offset in range(1, HORIZON_BARS + 2):
        valid &= session.eq(session.shift(-offset))
        delta = ts.shift(-offset) - ts.shift(-(offset - 1))
        valid &= delta.eq(pd.Timedelta(INTERVAL_MINUTES, unit="min"))
    features.loc[~valid, ["target_return_3", "Target"]] = np.nan

    features["news_available"] = (
        pd.to_numeric(features["news_event_count_24h"], errors="coerce")
        .fillna(0).gt(0).astype(int)
    )
    technical = list(TECHNICAL)
    volume = pd.to_numeric(features["volume_ratio"], errors="coerce")
    if not np.isfinite(volume.to_numpy(dtype=float)).any():
        technical.remove("volume_ratio")
    columns_all = technical + NEWS + ["news_available"]
    clean = (
        features.replace([np.inf, -np.inf], np.nan)
        .dropna(subset=columns_all + ["Target", "target_return_3", "timestamp"])
        .sort_values("timestamp").reset_index(drop=True)
    )
    if len(clean) < 100:
        raise RuntimeError(f"Only {len(clean)} usable rows; minimum is 100.")

    feature_sets = {
        "A_technical_only": technical,
        "B_technical_plus_news": technical + NEWS,
        "C_technical_news_plus_availability": technical + NEWS + ["news_available"],
    }
    news_rows = int(clean["news_event_count_24h"].gt(0).sum())
    metadata = {
        "symbol": symbol, "instrument_key": instrument_key,
        "provider": "Upstox V3 historical + intraday",
        "historical_candles": len(hist), "intraday_candles_received": len(live),
        "completed_merged_candles": len(candles),
        "latest_completed_candle_close": latest_close.isoformat(),
        "matching_news_records": len(payload),
        "usable_observations": len(clean),
        "rows_with_news": news_rows,
        "news_coverage": news_rows / len(clean),
        "first_observation": clean["timestamp"].iloc[0].isoformat(),
        "last_observation": clean["timestamp"].iloc[-1].isoformat(),
    }
    print(
        f"[{symbol}] usable={len(clean)}, news={news_rows}/{len(clean)} "
        f"({news_rows / len(clean):.2%})"
    )
    return clean, feature_sets, metadata


def evaluate_stock(symbol: str, clean: pd.DataFrame, feature_sets: dict):
    n = len(clean)
    initial = max(40, int(n * 0.50))
    remaining = n - initial
    if remaining < FOLDS * 5:
        raise RuntimeError(f"{symbol}: insufficient observations for {FOLDS} folds.")
    sizes = np.full(FOLDS, remaining // FOLDS, dtype=int)
    sizes[:remaining % FOLDS] += 1
    cursor = initial
    records = []
    factories = model_factories()

    for fold_no, size in enumerate(sizes, start=1):
        train = clean.iloc[:max(0, cursor - 4)].copy()
        test = clean.iloc[cursor:cursor + int(size)].copy()
        cursor += int(size)
        if train.empty or test.empty:
            continue
        y_train = train["Target"].astype(int)
        y_test = test["Target"].astype(int)
        if y_train.nunique() < 2:
            raise RuntimeError(f"{symbol} fold {fold_no}: training contains one class.")

        # Majority baseline is estimated only from this fold's training data.
        majority_class = int(y_train.mean() >= 0.5)
        majority_pred = np.full(len(test), majority_class, dtype=int)
        baseline = confusion_metrics(y_test, majority_pred)

        for set_name, columns in feature_sets.items():
            for model_name, factory in factories.items():
                # Trading threshold is selected on an earlier, purged validation
                # segment. It is not used for the classification metrics below.
                validation_size = max(12, int(len(train) * 0.20))
                split_idx = len(train) - validation_size - 4
                selection = {
                    "status": "insufficient_validation_data",
                    "selected_threshold": None,
                    "selection_data": "validation_only",
                }
                trading_threshold = 1.0
                if split_idx >= 40:
                    threshold_train = train.iloc[:split_idx].copy()
                    validation = train.iloc[split_idx + 4:].copy()
                    if len(validation) >= 12 and threshold_train["Target"].nunique() == 2:
                        threshold_model = fit_model(factory, threshold_train, columns)
                        validation_probs = positive_probabilities(
                            threshold_model, validation, columns
                        )
                        selection = _select_threshold_from_validation(
                            validation, validation_probs,
                            cost_bps=COST_BPS_PER_SIDE,
                            horizon_bars=HORIZON_BARS,
                            min_trades=MIN_VALIDATION_TRADES,
                        )
                        if selection["status"] == "selected_on_validation":
                            trading_threshold = float(selection["selected_threshold"])

                model = fit_model(factory, train, columns)
                probs = positive_probabilities(model, test, columns)

                # Probability classification threshold is fixed at 0.50.
                # Keep estimator.predict only as a diagnostic, not the primary
                # reported classification result.
                pred_050 = (probs >= 0.50).astype(int)
                estimator_pred = np.asarray(model.predict(test[columns]), dtype=int)
                cls = confusion_metrics(y_test, pred_050)
                estimator_cls = confusion_metrics(y_test, estimator_pred)

                auc = (
                    float(roc_auc_score(y_test, probs))
                    if y_test.nunique() > 1 else None
                )
                pr_auc = (
                    float(average_precision_score(y_test, probs))
                    if y_test.nunique() > 1 else None
                )
                bt = _non_overlapping_long_flat_backtest(
                    test, probs, cost_bps=COST_BPS_PER_SIDE,
                    threshold=trading_threshold, horizon_bars=HORIZON_BARS,
                )
                records.append({
                    "symbol": symbol, "feature_set": set_name,
                    "model": model_name, "fold": fold_no,
                    "feature_count": len(columns),
                    "train_observations": len(train),
                    "test_observations": len(test),
                    "test_start": test["timestamp"].iloc[0].isoformat(),
                    "test_end": test["timestamp"].iloc[-1].isoformat(),
                    "train_positive_rate": float(y_train.mean()),
                    "test_positive_rate": float(y_test.mean()),
                    "majority_baseline_class": majority_class,
                    "majority_baseline_accuracy": baseline["accuracy"],
                    "majority_baseline_balanced_accuracy": baseline["balanced_accuracy"],
                    **cls,
                    "estimator_predict_accuracy": estimator_cls["accuracy"],
                    "estimator_predict_balanced_accuracy": estimator_cls["balanced_accuracy"],
                    "estimator_predict_positive_rate": estimator_cls["prediction_positive_rate"],
                    "roc_auc": auc, "pr_auc": pr_auc,
                    "brier_score": float(brier_score_loss(y_test, probs)),
                    "log_loss": float(log_loss(y_test, probs, labels=[0, 1])),
                    "ece": _expected_calibration_error(y_test, probs),
                    "probability_mean": float(probs.mean()),
                    "probability_min": float(probs.min()),
                    "probability_median": float(np.median(probs)),
                    "probability_max": float(probs.max()),
                    "trading_threshold_status": selection["status"],
                    "trading_threshold": trading_threshold,
                    "threshold_selection": selection,
                    **bt,
                })
                print(
                    f"[{symbol}] fold={fold_no} {set_name} {model_name} "
                    f"BA@0.50={cls['balanced_accuracy']:.3f} "
                    f"PR-AUC={pr_auc if pr_auc is not None else 'NA'} "
                    f"trades={bt.get('trades', 0)}"
                )
    return records


def main():
    all_records = []
    metadata = {}
    failures = {}
    for symbol, key in STOCKS.items():
        try:
            clean, feature_sets, meta = prepare_stock(symbol, key)
            metadata[symbol] = meta
            all_records.extend(evaluate_stock(symbol, clean, feature_sets))
        except Exception as exc:
            failures[symbol] = f"{type(exc).__name__}: {exc}"
            print(f"[{symbol}] FAILED: {failures[symbol]}")
    if not all_records:
        raise RuntimeError("No stock completed. Check Upstox, PostgreSQL and API logs.")

    detail = pd.DataFrame(all_records)
    group_keys = ["symbol", "feature_set", "model"]
    fold_metric_cols = [
        "accuracy", "balanced_accuracy", "precision", "recall", "f1", "mcc",
        "roc_auc", "pr_auc", "brier_score", "log_loss", "ece",
        "prediction_positive_rate", "probability_mean",
        "majority_baseline_accuracy", "majority_baseline_balanced_accuracy",
        "net_return_pct", "gross_benchmark_return_pct", "max_drawdown",
    ]
    per_stock = (
        detail.groupby(group_keys, dropna=False)[fold_metric_cols + ["trades"]]
        .mean(numeric_only=True).reset_index()
        .rename(columns={c: f"mean_fold_{c}" for c in fold_metric_cols + ["trades"]})
    )
    pooled_rows = []
    for group_id, group in detail.groupby(group_keys, dropna=False):
        row = dict(zip(group_keys, group_id))
        row.update(pooled_confusion_metrics(group))
        pooled_rows.append(row)
    pooled = pd.DataFrame(pooled_rows)
    trade_totals = (
        detail.groupby(group_keys)["trades"].sum()
        .rename("total_test_trades").reset_index()
    )
    per_stock = per_stock.merge(pooled, on=group_keys).merge(
        trade_totals, on=group_keys
    )

    # Equal-stock macro uses per-stock pooled classification metrics, so each
    # stock has equal weight. It is not a combined portfolio return.
    macro_cols = [
        "pooled_accuracy", "pooled_balanced_accuracy", "pooled_precision",
        "pooled_recall", "pooled_f1", "mean_fold_roc_auc",
        "mean_fold_pr_auc", "mean_fold_brier_score", "mean_fold_log_loss",
        "mean_fold_ece", "mean_fold_net_return_pct",
    ]
    macro = (
        per_stock.groupby(["feature_set", "model"], dropna=False)[macro_cols]
        .mean(numeric_only=True).reset_index()
    )
    macro = macro.merge(
        per_stock.groupby(["feature_set", "model"])["total_test_trades"]
        .sum().rename("total_test_trades_across_stocks").reset_index(),
        on=["feature_set", "model"],
    )

    out = Path.cwd() / "research_outputs"
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    detail_path = out / f"bharatstock-five-stock-ablation-v2-{stamp}.csv"
    stock_path = out / f"bharatstock-five-stock-ablation-v2-by-stock-{stamp}.csv"
    macro_path = out / f"bharatstock-five-stock-ablation-v2-macro-{stamp}.csv"
    json_path = out / f"bharatstock-five-stock-ablation-v2-{stamp}.json"
    detail.to_csv(detail_path, index=False)
    per_stock.to_csv(stock_path, index=False)
    macro.to_csv(macro_path, index=False)

    payload = {
        "status": "completed_with_failures" if failures else "completed",
        "completed_stocks": list(metadata),
        "failed_stocks": failures,
        "stock_metadata": metadata,
        "method": (
            "Three expanding chronological test folds; four-row purge; same-session "
            "target windows; 0.50 probability threshold for classification; trading "
            "threshold selected only on an earlier purged validation slice."
        ),
        "models": list(model_factories()),
        "feature_sets": {
            "A_technical_only": "Technical indicators",
            "B_technical_plus_news": "Technical indicators + point-in-time news",
            "C_technical_news_plus_availability": "Set B + news_available indicator",
        },
        "cost_assumption": {
            "one_way_bps": COST_BPS_PER_SIDE,
            "round_trip_bps": 2 * COST_BPS_PER_SIDE,
            "note": "Cost proxy only, not complete Indian brokerage, taxes, spread or slippage.",
        },
        "aggregation": {
            "mean_fold_metrics": "Arithmetic mean of each stock's fold metrics.",
            "pooled_metrics": "Confusion counts summed across folds, then metrics derived.",
            "macro": "Equal-stock mean of per-stock pooled metrics; not a portfolio return.",
        },
        "limitations": [
            "Three folds are an initial research comparison, not proof of generalization.",
            "News coverage may be sparse and missing news is represented neutrally.",
            "Sentiment uses the project's existing keyword baseline.",
            "Class-weight comparisons do not guarantee improved prediction quality.",
            "No orders are placed and no trading readiness is inferred.",
        ],
        "per_stock_summary": per_stock.replace({np.nan: None}).to_dict("records"),
        "equal_stock_macro_summary": macro.replace({np.nan: None}).to_dict("records"),
        "fold_results": detail.replace({np.nan: None}).to_dict("records"),
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print("\n=== EQUAL-STOCK MACRO SUMMARY ===")
    print(macro.to_string(index=False))
    print("\n=== PER-STOCK POOLED CLASSIFICATION SUMMARY ===")
    print(per_stock[
        ["symbol", "feature_set", "model", "pooled_accuracy",
         "pooled_balanced_accuracy", "pooled_precision", "pooled_recall",
         "pooled_f1", "mean_fold_pr_auc", "total_test_trades"]
    ].to_string(index=False))
    print("\nCompleted stocks:", ", ".join(metadata))
    if failures:
        print("Failed stocks:", json.dumps(failures, indent=2))
    print(f"\nDetailed folds: {detail_path}")
    print(f"Per-stock summary: {stock_path}")
    print(f"Macro summary: {macro_path}")
    print(f"Full JSON: {json_path}")


if __name__ == "__main__":
    main()
