import numpy as np
import pandas as pd


def test_model_registry_saves_and_reloads_artifact(tmp_path, monkeypatch):
    import app.model_registry as registry

    monkeypatch.setenv("BHARATSTOCK_MODEL_DIR", str(tmp_path / "artifacts"))
    rng = np.random.default_rng(2026)
    n = 180
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    target = (x1 + 0.25 * x2 > 0).astype(int)
    frame = pd.DataFrame({"x1": x1, "x2": x2, "Target": target},
                         index=pd.date_range("2020-01-01", periods=n, freq="B"))

    first_model, first_meta = registry.load_or_train("TEST.NS", frame, ["x1", "x2"])
    assert first_meta["artifact_status"] == "trained_and_saved"
    assert (tmp_path / "artifacts" / "TEST.NS-bharatstock-rf-et-v1.joblib").exists()

    second_model, second_meta = registry.load_or_train("TEST.NS", frame, ["x1", "x2"])
    assert second_meta["artifact_status"] == "loaded"
    np.testing.assert_array_equal(
        first_model.predict_proba(frame[["x1", "x2"]]),
        second_model.predict_proba(frame[["x1", "x2"]]),
    )


def test_model_registry_rejects_missing_feature_schema(tmp_path, monkeypatch):
    import pytest
    import app.model_registry as registry

    monkeypatch.setenv("BHARATSTOCK_MODEL_DIR", str(tmp_path))
    frame = pd.DataFrame({"x1": [0, 1], "Target": [0, 1]})
    with pytest.raises(ValueError, match="feature schema"):
        registry.load_or_train("TEST.NS", frame, ["missing"])
