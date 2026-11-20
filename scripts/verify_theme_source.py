from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
checks = {
    'theme toggle exists': "setTheme(current=>current==='dark'?'light':'dark')" in app,
    'theme preference persists': "localStorage.setItem('bharatstock.theme',theme)" in app,
    'custom SVG chart grid adapts to theme': "grid:theme==='light'?'#e2e8f0':'#263449'" in app,
    'chart inspection strip exposes current OHLC values': all(f'<span>{k} <b>' in app for k in ['O','H','L']) and '<span className={current.Close>=current.Open?' in app,
    'light form controls styled': '[data-theme="light"] :is(input,select,textarea)' in css,
    'light placeholders styled': '[data-theme="light"] :is(input,select,textarea)::placeholder' in css,
    'reduced motion supported': '@media (prefers-reduced-motion: reduce)' in css,
    'no hardcoded demo-price source added': 'DEMO_PRICE_SOURCE' not in app,
}
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if not all(checks.values()):
    raise SystemExit(1)
print(f"{sum(checks.values())}/{len(checks)} source checks passed")
