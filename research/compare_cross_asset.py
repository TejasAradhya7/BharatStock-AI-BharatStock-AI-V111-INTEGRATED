import json
import csv
from pathlib import Path

folder = Path("research_results")
rows = []

for path in sorted(folder.glob("*_feature_experiments.json")):
    report = json.loads(path.read_text(encoding="utf-8"))
    symbol = report.get("symbol", path.stem)

    for result in report.get("results", []):
        mean = result["mean"]
        folds = result.get("folds", [])
        rows.append({
            "symbol": symbol,
            "feature_set": result["feature_set"],
            "model": result["model"],
            "accuracy_pct": round(mean["accuracy"] * 100, 2),
            "balanced_accuracy_pct": round(mean["balanced_accuracy"] * 100, 2),
            "majority_accuracy_pct": round(mean["majority_accuracy"] * 100, 2),
            "accuracy_minus_majority_pp": round(
                result["accuracy_minus_majority"] * 100, 2
            ),
            "brier_score": round(mean["brier_score"], 4),
            "folds_above_majority": sum(
                f["accuracy"] > f["majority_accuracy"] for f in folds
            ),
            "fold_count": len(folds),
            "observations": report.get("observations")
        })

if not rows:
    raise SystemExit("No research JSON files found in research_results.")

output = Path("research_results") / "cross_asset_comparison.csv"
with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved: {output}")
print(f"Experiments: {len(rows)}")
print("\nTop results by balanced accuracy:")
for row in sorted(rows, key=lambda x: x["balanced_accuracy_pct"], reverse=True)[:15]:
    print(
        f'{row["symbol"]:12} {row["feature_set"]:12} '
        f'{row["model"]:20} '
        f'Balanced={row["balanced_accuracy_pct"]:.2f}% '
        f'Accuracy={row["accuracy_pct"]:.2f}% '
        f'Majority={row["majority_accuracy_pct"]:.2f}% '
        f'Folds above baseline={row["folds_above_majority"]}/{row["fold_count"]}'
    )
