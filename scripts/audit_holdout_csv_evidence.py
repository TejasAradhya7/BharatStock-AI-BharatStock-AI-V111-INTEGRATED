#!/usr/bin/env python3
"""Recompute classification metrics from supplied holdout CSVs and audit evidence limits.

Run from project root:
  python scripts/audit_holdout_csv_evidence.py
Inputs are reports/evidence/bharatstock_holdout_predictions_h{1,3,5,10}.csv and
reports/evidence/bharatstock_multihorizon_metrics.csv. This does not claim to
reproduce historical returns: prediction CSVs do not include executable prices.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, brier_score_loss, log_loss)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "reports" / "evidence"
OUT = ROOT / "reports"

def audit_one(horizon: int) -> dict:
    path = EVIDENCE / f"bharatstock_holdout_predictions_h{horizon}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing required evidence file: {path}")
    df = pd.read_csv(path)
    required = {"actual", "prob_up"}
    if not required.issubset(df.columns):
        raise ValueError(f"{path.name} must contain actual and prob_up columns")
    if "Date" in df and "date" in df and not (df["Date"].astype(str) == df["date"].astype(str)).all():
        raise ValueError(f"{path.name} has conflicting Date and date columns")
    y = pd.to_numeric(df["actual"], errors="coerce")
    p = pd.to_numeric(df["prob_up"], errors="coerce")
    if y.isna().any() or p.isna().any():
        raise ValueError(f"{path.name} contains missing/non-numeric labels or probabilities")
    if not set(y.unique()).issubset({0, 1}):
        raise ValueError(f"{path.name} actual must contain only binary 0/1 labels")
    if ((p < 0) | (p > 1)).any():
        raise ValueError(f"{path.name} prob_up must be in [0, 1]")
    if "Date" in df:
        dates = pd.to_datetime(df["Date"], errors="coerce")
        if dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing:
            raise ValueError(f"{path.name} dates must be valid, unique, and increasing")
    pred = (p >= 0.5).astype(int)
    return {"horizon_bars": horizon, "rows": int(len(df)),
        "date_start": str(df["Date"].iloc[0]) if "Date" in df and len(df) else None,
        "date_end": str(df["Date"].iloc[-1]) if "Date" in df and len(df) else None,
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, p)) if y.nunique() == 2 else None,
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "threshold": 0.5,
        "source_file": path.name}

def main() -> int:
    rows = [audit_one(h) for h in (1, 3, 5, 10)]
    metrics_path = EVIDENCE / "bharatstock_multihorizon_metrics.csv"
    source_metrics = pd.read_csv(metrics_path) if metrics_path.exists() else pd.DataFrame()
    for row in rows:
        match = source_metrics[source_metrics["horizon_bars"] == row["horizon_bars"]] if "horizon_bars" in source_metrics else pd.DataFrame()
        # Exact model rows should match recomputation; the CSV does not explicitly link each
        # prediction file to its model, so compare against any row with matching metrics.
        row["matching_metrics_row_found"] = bool(len(match) and any(
            np.isclose(float(m["accuracy"]), row["accuracy"], atol=1e-9) and
            np.isclose(float(m["roc_auc"]), row["roc_auc"], atol=1e-9)
            for _, m in match.iterrows()))
    OUT.mkdir(exist_ok=True)
    report = {"status": "passed" if all(r["matching_metrics_row_found"] for r in rows) else "review_required",
        "classification_metrics_recomputed": rows,
        "backtest_audit": {"status": "not_fully_reproducible_from_supplied_csvs",
          "reason": "The holdout prediction CSVs contain labels and probabilities but no entry/exit close prices or per-trade returns. The supplied backtest summary cannot independently establish signal timing, matched benchmark, or cost application without its price-aligned trade ledger and benchmark CSV.",
          "reported_backtest_summary_file": "bharatstock_after_cost_backtest.csv",
          "required_next_artifact": "price-aligned trade ledger with signal timestamp, entry timestamp/price, exit timestamp/price, gross return, cost, net return, strategy equity, benchmark equity"},
        "limitations": ["Recomputed classification metrics validate consistency with the supplied prediction CSVs, not the model training process or absence of data leakage.",
          "The supplied predictions use the fixed probability threshold 0.5 for classification metrics.",
          "A result above 50% accuracy does not establish a profitable or robust trading strategy."]}
    (OUT / "holdout_evidence_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT / "holdout_evidence_metrics_recomputed.csv", index=False)
    print(json.dumps({"status": report["status"], "rows": rows,
                      "backtest_audit": report["backtest_audit"]}, indent=2))
    return 0 if report["status"] == "passed" else 2

if __name__ == "__main__":
    raise SystemExit(main())
