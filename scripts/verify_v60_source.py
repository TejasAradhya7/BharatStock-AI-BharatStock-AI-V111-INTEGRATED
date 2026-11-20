from pathlib import Path
root = Path(__file__).resolve().parents[1]
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
checks = {
    'professional font stack includes IBM Plex Mono for market numbers': "'IBM Plex Mono'" in css,
    'dark trading-terminal design tokens exist': '--bs-surface: #0e1827' in css and '--bs-accent: #19b88a' in css,
    'light theme overrides trading surfaces': '[data-theme="light"] .panel' in css and '[data-theme="light"] .liveQuote' in css,
    'numeric quote typography uses tabular figures': 'font-variant-numeric: tabular-nums' in css,
    'candlestick interval toolbar styling exists': '.intervalToolbar' in css and '.intervalButton.active' in css,
    'candlestick OHLC strip styling exists': '.ohlcStrip' in css and '.tradingSvg' in css,
    'responsive mobile styles retained': '@media (max-width: 720px)' in css,
    'reduced-motion support retained': '@media (prefers-reduced-motion: reduce)' in css,
    'theme preference and toggle remain wired': "localStorage.setItem('bharatstock.theme',theme)" in app and 'setTheme(current=>' in app,
    'real provider OHLC chart retained': '/api/chart/${encodeURIComponent(symbol)}' in app and 'No sample candles are generated.' in app,
}
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if not all(checks.values()):
    raise SystemExit(1)
print(f'{sum(checks.values())}/{len(checks)} V60 source checks passed')
