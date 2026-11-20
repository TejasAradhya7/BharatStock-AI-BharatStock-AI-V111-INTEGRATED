from pathlib import Path

path = Path("services/api/app/multi_stock_calibration_v4.py")
content = path.read_text(encoding="utf-8-sig")

def replace_once(old, new, description):
    global content
    count = content.count(old)
    if count != 1:
        raise RuntimeError(
            f"{description}: expected exactly 1 match, found {count}. "
            "No file has been written."
        )
    content = content.replace(old, new, 1)
    print("PATCHED:", description)

replace_once(
    '"""BharatStock AI: five-stock leakage-aware intraday model evaluation V2.',
    '"""BharatStock AI: V4 five-stock calibration comparison.',
    "V4 docstring",
)

replace_once(
'''def fit_model(factory, train: pd.DataFrame, columns: list[str]):
    """Fit using the project's chronological sigmoid-calibration helper."""
    # The existing helper uses TimeSeriesSplit(n_splits=3, gap=4) when possible.
    return fit_probability_model(factory, train, columns)
''',
'''def fit_model(
    factory,
    train: pd.DataFrame,
    columns: list[str],
    calibration_method: str,
):
    """Fit either directly or with the existing chronological sigmoid calibration."""
    y_train = train["Target"].astype(int)

    if calibration_method == "sigmoid":
        return fit_probability_model(factory, train, columns)

    if calibration_method == "uncalibrated":
        model = factory()
        model.fit(train[columns], y_train)
        return model

    raise ValueError(f"Unknown calibration method: {calibration_method}")
''',
    "calibration-aware fit_model",
)

replace_once(
    '    factories = model_factories()\n',
'''    base_factories = model_factories()
    factories = {
        f"{model_name}__{method}": (model_name, factory, method)
        for model_name, factory in base_factories.items()
        for method in ("uncalibrated", "sigmoid")
    }
''',
    "paired model variants",
)

replace_once(
    '            for model_name, factory in factories.items():\n',
    '            for variant_name, (model_name, factory, calibration_method) in factories.items():\n',
    "model evaluation loop",
)

replace_once(
    'threshold_model = fit_model(factory, threshold_train, columns)',
    'threshold_model = fit_model(factory, threshold_train, columns, calibration_method)',
    "validation model calibration",
)

replace_once(
    '                model = fit_model(factory, train, columns)',
    '                model = fit_model(factory, train, columns, calibration_method)',
    "test model calibration",
)

replace_once(
    '                    "symbol": symbol, "feature_set": set_name,\n                    "model": model_name, "fold": fold_no,',
    '                    "symbol": symbol, "feature_set": set_name,\n                    "model": model_name, "calibration_method": calibration_method,\n                    "fold": fold_no,',
    "record calibration method",
)

replace_once(
    '                    f"[{symbol}] fold={fold_no} {set_name} {model_name} "\n',
    '                    f"[{symbol}] fold={fold_no} {set_name} {model_name} "\n                    f"calibration={calibration_method} "\n',
    "console calibration label",
)

replace_once(
    '    group_keys = ["symbol", "feature_set", "model"]',
    '    group_keys = ["symbol", "feature_set", "model", "calibration_method"]',
    "aggregation grouping",
)

replace_once(
    '    macro = (\n        per_stock.groupby(["feature_set", "model"], dropna=False)[macro_cols]',
    '    macro = (\n        per_stock.groupby(["feature_set", "model", "calibration_method"], dropna=False)[macro_cols]',
    "macro grouping",
)

replace_once(
    '        per_stock.groupby(["feature_set", "model"])["total_test_trades"]',
    '        per_stock.groupby(["feature_set", "model", "calibration_method"])["total_test_trades"]',
    "macro trade grouping",
)

replace_once(
    '        on=["feature_set", "model"],\n',
    '        on=["feature_set", "model", "calibration_method"],\n',
    "macro merge key",
)

replace_once(
    'bharatstock-five-stock-ablation-v2-{stamp}.csv',
    'bharatstock-five-stock-calibration-v4-{stamp}.csv',
    "V4 detail filename",
)

replace_once(
    'bharatstock-five-stock-ablation-v2-by-stock-{stamp}.csv',
    'bharatstock-five-stock-calibration-v4-by-stock-{stamp}.csv',
    "V4 stock filename",
)

replace_once(
    'bharatstock-five-stock-ablation-v2-macro-{stamp}.csv',
    'bharatstock-five-stock-calibration-v4-macro-{stamp}.csv',
    "V4 macro filename",
)

replace_once(
    '        "models": list(model_factories()),\n',
    '        "models": list(model_factories()),\n'
    '        "calibration_methods": ["uncalibrated", "sigmoid"],\n',
    "JSON calibration metadata",
)

replace_once(
    '            "Three expanding chronological test folds; four-row purge; same-session "\n'
    '            "target windows; 0.50 probability threshold for classification; trading "\n'
    '            "threshold selected only on an earlier purged validation slice."\n',
    '            "Paired uncalibrated and chronological sigmoid-calibrated models; "\n'
    '            "three expanding chronological test folds; four-row purge; same-session "\n'
    '            "target windows; 0.50 probability threshold for classification; trading "\n'
    '            "threshold selected only on an earlier purged validation slice."\n',
    "V4 methodology description",
)

replace_once(
    '        "limitations": [\n',
    '        "limitations": [\n'
    '            "Calibration comparison is an initial research experiment, not proof of generalization.",\n'
    '            "Sigmoid calibration uses the existing chronological TimeSeriesSplit helper.",\n',
    "V4 limitations",
)

# Use a V4-specific JSON filename as well.
replace_once(
    'bharatstock-five-stock-ablation-v2-{stamp}.json',
    'bharatstock-five-stock-calibration-v4-{stamp}.json',
    "V4 JSON filename",
)

path.write_text(content, encoding="utf-8")
print("\\nV4 patch completed:", path)
print("V3 source and backup were not changed.")
