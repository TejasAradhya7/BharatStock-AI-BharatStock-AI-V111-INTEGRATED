from pathlib import Path
root = Path(__file__).resolve().parents[1]
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
checks = {
    'five navigation pages': all(x in app for x in ["'overview'", "'market-analysis'", "'ai-predictions'", "'risk-lab'", "'demo-trading'"]),
    'browser history route sync': 'window.addEventListener(\'popstate\', syncRoute)' in app,
    'page-based main root': 'data-page={activeSection}' in app,
    'demo trading page anchor': 'id="demo-trading"' in app,
    'overview page CSS': 'main[data-page="overview"]' in css,
    'market analysis page CSS': 'main[data-page="market-analysis"]' in css,
    'AI predictions page CSS': 'main[data-page="ai-predictions"]' in css,
    'risk lab page CSS': 'main[data-page="risk-lab"]' in css,
    'demo trading page CSS': 'main[data-page="demo-trading"]' in css,
    'mobile navigation styling': '@media (max-width: 720px)' in css and '.sidebar a { display: flex' in css,
}
for label, ok in checks.items(): print(('PASS' if ok else 'FAIL') + ' ' + label)
if not all(checks.values()): raise SystemExit(1)
