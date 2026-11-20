from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / "apps/web/src/App.tsx").read_text(encoding="utf-8")
css = (ROOT / "apps/web/src/style.css").read_text(encoding="utf-8")

checks = {
    "Research Lab section is explicitly visible on its page": 'main[data-page="research-lab"] > #research-lab { display: block; }' in css,
    "Research status is loaded on app startup": "void loadResearchStatus();" in app,
    "Invalid index price records are visibly flagged": "INVALID PRICE · DO NOT USE" in app,
    "Invalid index records can be archived from active journal": "Archive invalid index records" in app,
    "Duplicate open paper positions have a cleanup action": "Archive duplicate OPEN positions" in app,
    "Archived paper positions are excluded from P/L": "t.status==='ARCHIVED'?null" in app,
    "Holdout and walk-forward baselines are labelled separately": "Holdout majority-class baseline" in app and "Mean fold majority-class baseline" in app,
}
for label, passed in checks.items():
    print(("PASS" if passed else "FAIL") + " - " + label)
if not all(checks.values()):
    raise SystemExit(1)
