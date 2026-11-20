from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
checks = {
    'live quote stale warning': 'treat quotes as stale' in app,
    'stale threshold 30 seconds': 'liveTickAgeMs>30000' in app,
    'prediction baseline caveat': 'training-only baseline' in app and 'weak evidence' in app,
    'prediction research-only disclaimer': 'not a buy or sell instruction' in app,
    'prediction caution style': '.predictionCaution' in css,
    'existing stress input validation': 'Scenario shock must be between -100% and +100%.' in app,
    'existing no demo-data fallback': 'Data unavailable — no demo prices substituted' in app,
}
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if not all(checks.values()):
    raise SystemExit(1)
print(f'{sum(checks.values())}/{len(checks)} checks passed')
