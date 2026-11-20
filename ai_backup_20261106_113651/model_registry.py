"""Persistent, versioned model artifacts for the live prediction API.

Research candidates are deliberately not auto-promoted. Until a candidate clears
future-period confirmation, the established RF + Extra Trees ensemble remains
production model. Artifacts are keyed by symbol and training-data fingerprint.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, VotingClassifier

MODEL_VERSION = "bharatstock-rf-et-v1"


def _artifact_dir() -> Path:
    configured = os.getenv("BHARATSTOCK_MODEL_DIR")
    return Path(configured) if configured else Path(__file__).resolve().parents[1] / "model_artifacts"


def _fingerprint(frame: pd.DataFrame, features: Sequence[str]) -> str:
    # Include all labelled feature values and index; a new candle invalidates cache.
    digest = hashlib.sha256()
    digest.update(json.dumps(list(features), separators=(",", ":")).encode())
    digest.update(pd.util.hash_pandas_object(frame[list(features) + ["Target"]], index=True).values.tobytes())
    return digest.hexdigest()


def _new_model() -> VotingClassifier:
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=8, min_samples_leaf=5,
        max_features="sqrt", class_weight="balanced_subsample",
        random_state=42, n_jobs=1,
    )
    et = ExtraTreesClassifier(
        n_estimators=250, max_depth=8, min_samples_leaf=5,
        max_features="sqrt", class_weight="balanced",
        random_state=43, n_jobs=1,
    )
    return VotingClassifier(estimators=[("random_forest", rf), ("extra_trees", et)], voting="soft", weights=[1, 1], n_jobs=1)


def load_or_train(symbol: str, frame: pd.DataFrame, features: Sequence[str]):
    """Load a matching artifact or train and atomically persist the current ensemble."""
    if not features or any(name not in frame.columns for name in list(features) + ["Target"]):
        raise ValueError("Training frame does not match the declared feature schema")
    labelled = frame[list(features) + ["Target"]].replace([float("inf"), float("-inf")], float("nan")).dropna().copy()
    if len(labelled) < 100 or labelled["Target"].nunique() < 2:
        raise ValueError("Insufficient labelled observations or only one target class")
    labelled["Target"] = labelled["Target"].astype(int)
    fingerprint = _fingerprint(labelled, features)
    safe_symbol = "".join(ch for ch in symbol.upper() if ch.isalnum() or ch in "._-")
    path = _artifact_dir() / f"{safe_symbol}-{MODEL_VERSION}.joblib"
    if path.exists():
        try:
            payload = joblib.load(path)
            meta = payload.get("metadata", {})
            if (meta.get("model_version") == MODEL_VERSION
                    and meta.get("symbol") == symbol.upper()
                    and meta.get("features") == list(features)
                    and meta.get("training_fingerprint") == fingerprint):
                return payload["model"], {**meta, "artifact_status": "loaded"}
        except Exception:
            # Corrupt/incompatible artifacts are safely retrained below.
            pass
    model = _new_model()
    model.fit(labelled[list(features)], labelled["Target"])
    metadata = {
        "model_version": MODEL_VERSION,
        "model_name": "RandomForest + ExtraTrees soft-voting ensemble",
        "symbol": symbol.upper(),
        "features": list(features),
        "training_rows": int(len(labelled)),
        "training_start": str(labelled.index.min()),
        "training_end": str(labelled.index.max()),
        "training_fingerprint": fingerprint,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "artifact_status": "trained_and_saved",
        "promotion_policy": "conservative_existing_production_model; V94 research candidates not auto-promoted",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    try:
        joblib.dump({"model": model, "metadata": metadata}, temp_name)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return model, metadata
