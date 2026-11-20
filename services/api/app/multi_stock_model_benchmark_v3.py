"""BharatStock AI V3: walk-forward ML-vs-simple-baseline benchmark.

Run inside the API container:
    python -m app.multi_stock_model_benchmark_v3

This is a research-only benchmark. It does not change production predictions,
place orders, tune on the test folds, or claim trading readiness.
It reuses the V2 data preparation and model/calibration helpers so the test
observations and chronological folds remain comparable to V2.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score,
    brier_score_loss, confusion_matrix, f1_score, log_loss,
    matthews_corrcoef, precision_score, recall_score, roc_auc_score,
)

from . import multi_stock_feature_ablation as v2

FOLDS = v2.FOLDS
PURGE_ROWS = 4
CLASSIFICATION_THRESHOLD = 0.50


def metric_row(y_true, y_pred, probabilities=None):
    y = np.asarray(y_true, dtype=int)
    pred = np.asarray(y_pred, dtype=int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    out = {
        "observations": int(len(y)),
        "positive_rate_actual": float(y.mean()),
        "positive_rate_predicted": float(pred.mean()),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)) if len(np.unique(y)) > 1 else None,
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y, pred)),
    }
    if probabilities is not None:
        p = np.clip(np.asarray(probabilities, dtype=float), 1e-7, 1 - 1e-7)
        out.update({
            "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None,
            "pr_auc": float(average_precision_score(y, p)) if len(np.unique(y)) > 1 else None,
            "brier_score": float(brier_score_loss(y, p)),
            "log_loss": float(log_loss(y, p, labels=[0, 1])),
            "probability_mean": float(p.mean()),
        })
    else:
        out.update({k: None for k in ["roc_auc", "pr_auc", "brier_score", "log_loss", "probability_mean"]})
    return out


def baseline_predictions(test: pd.DataFrame, majority_class: int):
    """Causal rules using only features available at the signal candle close."""
    return {
        "Baseline_majority": np.full(len(test), majority_class, dtype=int),
        "Baseline_ret1_sign": (pd.to_numeric(test["ret_1"], errors="coerce").fillna(0).to_numpy() > 0).astype(int),
        "Baseline_ret3_sign": (pd.to_numeric(test["ret_3"], errors="coerce").fillna(0).to_numpy() > 0).astype(int),
        "Baseline_sma5_trend": (pd.to_numeric(test["sma_gap_5"], errors="coerce").fillna(0).to_numpy() > 0).astype(int),
    }


def evaluate_stock(symbol: str, clean: pd.DataFrame, feature_sets: dict):
    n = len(clean)
    initial = max(40, int(n * 0.50))
    remaining = n - initial
    if remaining < FOLDS * 5:
        raise RuntimeError(f"{symbol}: insufficient rows for {FOLDS} folds")
    sizes = np.full(FOLDS, remaining // FOLDS, dtype=int)
    sizes[:remaining % FOLDS] += 1
    cursor = initial
    records, errors = [], []
    factories = v2.model_factories()

    for fold, size in enumerate(sizes, start=1):
        train = clean.iloc[:max(0, cursor - PURGE_ROWS)].copy()
        test = clean.iloc[cursor:cursor + int(size)].copy()
        cursor += int(size)
        if train.empty or test.empty:
            continue
        y_train = train["Target"].astype(int)
        y_test = test["Target"].astype(int)
        if y_train.nunique() < 2:
            raise RuntimeError(f"{symbol} fold {fold}: training data contains one class")
        majority_class = int(y_train.mean() >= 0.5)

        # All baselines are evaluated on exactly the same held-out rows as ML.
        for baseline_name, pred in baseline_predictions(test, majority_class).items():
            row = {
                "symbol": symbol, "fold": fold, "evaluation_type": "simple_baseline",
                "feature_set": "not_applicable", "model": baseline_name,
                "train_observations": len(train),
                "test_start": test["timestamp"].iloc[0].isoformat(),
                "test_end": test["timestamp"].iloc[-1].isoformat(),
                **metric_row(y_test, pred),
            }
            records.append(row)

        # ML variants and feature sets match V2; threshold is fixed at 0.50.
        for set_name, columns in feature_sets.items():
            for model_name, factory in factories.items():
                try:
                    model = v2.fit_model(factory, train, columns)
                    probs = v2.positive_probabilities(model, test, columns)
                    pred = (np.asarray(probs) >= CLASSIFICATION_THRESHOLD).astype(int)
                    row = {
                        "symbol": symbol, "fold": fold, "evaluation_type": "machine_learning",
                        "feature_set": set_name, "model": model_name,
                        "train_observations": len(train),
                        "test_start": test["timestamp"].iloc[0].isoformat(),
                        "test_end": test["timestamp"].iloc[-1].isoformat(),
                        "classification_threshold": CLASSIFICATION_THRESHOLD,
                        **metric_row(y_test, pred, probs),
                    }
                    records.append(row)
                except Exception as exc:
                    errors.append({
                        "symbol": symbol, "fold": fold, "feature_set": set_name,
                        "model": model_name, "error": f"{type(exc).__name__}: {exc}",
                    })
    return records, errors


def pooled_metrics(group: pd.DataFrame):
    tn, fp, fn, tp = [int(group[c].sum()) for c in ["tn", "fp", "fn", "tp"]]
    n = tn + fp + fn + tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "pooled_observations": n,
        "pooled_accuracy": (tn + tp) / n if n else None,
        "pooled_balanced_accuracy": (recall + specificity) / 2 if n else None,
        "pooled_precision": precision, "pooled_recall": recall, "pooled_f1": f1,
        "pooled_mcc": float(matthews_corrcoef(
            np.r_[np.zeros(tn + fp, dtype=int), np.ones(fn + tp, dtype=int)],
            np.r_[np.r_[np.zeros(tn, dtype=int), np.ones(fp, dtype=int)], np.r_[np.zeros(fn, dtype=int), np.ones(tp, dtype=int)]]
        )) if n else None,
    }


def main():
    all_rows, all_errors, metadata, stock_failures = [], [], {}, {}
    for symbol, key in v2.STOCKS.items():
        try:
            clean, feature_sets, meta = v2.prepare_stock(symbol, key)
            metadata[symbol] = meta
            rows, errors = evaluate_stock(symbol, clean, feature_sets)
            all_rows.extend(rows)
            all_errors.extend(errors)
        except Exception as exc:
            stock_failures[symbol] = f"{type(exc).__name__}: {exc}"
            print(f"[{symbol}] FAILED: {stock_failures[symbol]}")

    if not all_rows:
        raise RuntimeError("No benchmark rows produced; inspect Upstox, DB and V2 module.")
    detail = pd.DataFrame(all_rows)
    group_keys = ["symbol", "evaluation_type", "feature_set", "model"]
    pooled_rows = []
    for key_tuple, group in detail.groupby(group_keys, dropna=False):
        row = dict(zip(group_keys, key_tuple))
        row.update(pooled_metrics(group))
        # Fold averages and spread show whether one fold dominates.
        for metric in ["accuracy", "balanced_accuracy", "f1", "mcc", "roc_auc", "pr_auc", "brier_score"]:
            vals = pd.to_numeric(group[metric], errors="coerce").dropna()
            row[f"mean_fold_{metric}"] = float(vals.mean()) if len(vals) else None
            row[f"std_fold_{metric}"] = float(vals.std(ddof=0)) if len(vals) else None
        row["total_test_trades"] = None  # V3 is a prediction benchmark, not a trading simulation.
        pooled_rows.append(row)
    by_stock = pd.DataFrame(pooled_rows)

    macro_keys = ["evaluation_type", "feature_set", "model"]
    macro_metrics = [
        "pooled_accuracy", "pooled_balanced_accuracy", "pooled_precision",
        "pooled_recall", "pooled_f1", "pooled_mcc", "mean_fold_roc_auc",
        "mean_fold_pr_auc", "mean_fold_brier_score",
    ]
    macro = by_stock.groupby(macro_keys, dropna=False)[macro_metrics].mean(numeric_only=True).reset_index()
    macro["stocks_included"] = by_stock.groupby(macro_keys, dropna=False)["symbol"].nunique().values
    macro["aggregation"] = "equal-stock mean of per-stock pooled metrics; not portfolio performance"

    # Direct model-vs-baseline deltas, matched by stock and fold-aggregated stock metrics.
    baseline = by_stock[by_stock.evaluation_type == "simple_baseline"][[
        "symbol", "model", "pooled_balanced_accuracy", "pooled_accuracy", "pooled_mcc"
    ]].rename(columns={
        "model": "baseline_model", "pooled_balanced_accuracy": "baseline_pooled_balanced_accuracy",
        "pooled_accuracy": "baseline_pooled_accuracy", "pooled_mcc": "baseline_pooled_mcc",
    })
    ml = by_stock[by_stock.evaluation_type == "machine_learning"].copy()
    deltas = []
    for _, m in ml.iterrows():
        for _, b in baseline[baseline.symbol == m.symbol].iterrows():
            deltas.append({
                "symbol": m.symbol, "feature_set": m.feature_set, "model": m.model,
                "baseline_model": b.baseline_model,
                "balanced_accuracy_delta_vs_baseline": m.pooled_balanced_accuracy - b.baseline_pooled_balanced_accuracy,
                "accuracy_delta_vs_baseline": m.pooled_accuracy - b.baseline_pooled_accuracy,
                "mcc_delta_vs_baseline": m.pooled_mcc - b.baseline_pooled_mcc,
            })
    delta_df = pd.DataFrame(deltas)

    out = Path.cwd() / "research_outputs"
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    detail_path = out / f"bharatstock-five-stock-v3-benchmark-{stamp}.csv"
    stock_path = out / f"bharatstock-five-stock-v3-by-stock-{stamp}.csv"
    macro_path = out / f"bharatstock-five-stock-v3-macro-{stamp}.csv"
    delta_path = out / f"bharatstock-five-stock-v3-baseline-deltas-{stamp}.csv"
    json_path = out / f"bharatstock-five-stock-v3-{stamp}.json"
    detail.to_csv(detail_path, index=False)
    by_stock.to_csv(stock_path, index=False)
    macro.to_csv(macro_path, index=False)
    delta_df.to_csv(delta_path, index=False)
    payload = {
        "status": "completed_with_errors" if stock_failures or all_errors else "completed",
        "completed_stocks": list(metadata), "failed_stocks": stock_failures,
        "model_errors": all_errors, "stock_metadata": metadata,
        "method": "Same V2 common rows, expanding chronological folds, four-row purge; all model classifications use fixed 0.50 probability threshold; simple baselines use only causal signal-time features.",
        "baselines": ["training majority class", "ret_1 sign", "ret_3 sign", "sma_gap_5 sign"],
        "models": list(v2.model_factories()),
        "feature_sets": ["A_technical_only", "B_technical_plus_news", "C_technical_news_plus_availability"],
        "limitations": [
            "This is a predictive benchmark, not a trading backtest or trading recommendation.",
            "Three test folds are preliminary and do not prove future generalization.",
            "News coverage remains limited in the V2 data source.",
            "No hyperparameter search is performed on test folds.",
            "Equal-stock macro metrics are not a portfolio result.",
        ],
        "macro_summary": macro.replace({np.nan: None}).to_dict("records"),
        "by_stock_summary": by_stock.replace({np.nan: None}).to_dict("records"),
        "baseline_deltas": delta_df.replace({np.nan: None}).to_dict("records"),
        "fold_results": detail.replace({np.nan: None}).to_dict("records"),
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print("\n=== V3 EQUAL-STOCK MACRO SUMMARY ===")
    print(macro.to_string(index=False))
    print("\n=== V3 BASELINE DELTAS (per stock) ===")
    print(delta_df.to_string(index=False))
    print("\nCompleted stocks:", ", ".join(metadata))
    if stock_failures:
        print("Failed stocks:", json.dumps(stock_failures, indent=2))
    if all_errors:
        print(f"Model-level errors: {len(all_errors)} (see JSON)")
    print(f"\nDetailed folds: {detail_path}")
    print(f"Per-stock summary: {stock_path}")
    print(f"Macro summary: {macro_path}")
    print(f"Baseline deltas: {delta_path}")
    print(f"Full JSON: {json_path}")


if __name__ == "__main__":
    main()
