from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
upstox = (root / 'services/api/app/upstox.py').read_text(encoding='utf-8')
checks = {
    'heatmap section exists': 'Stock heatmap' in app and 'aria-labelledby="heatmap-title"' in app,
    'filter controls exist': "'gainers'" in app and "'losers'" in app and 'aria-pressed' in app,
    'heatmap uses provider quote changes': 'q.change_pct' in app and 'q.last_price' in app,
    'no fabricated heatmap quote values': "'Change unavailable'" in app and "'Unavailable'" in app,
    'heatmap click opens market analysis': 'void loadMarket(key,period)' in app,
    'zero-only index volume is not presented as meaningful volume': 'volumeAvailable=valid.some(b=>b.Volume!=null&&Number(b.Volume)>0)' in app and 'VOLUME · unavailable from provider' in app,
    'expanded symbols included in quote request': 'TATAMOTORS.NS' in app and 'SUNPHARMA.NS' in app,
    'instrument mappings exist': all(k in upstox for k in ['ITC.NS','HINDUNILVR.NS','LT.NS','BHARTIARTL.NS','AXISBANK.NS','KOTAKBANK.NS','MARUTI.NS','SUNPHARMA.NS','TATAMOTORS.NS']),
    'responsive and theme styles exist': '.stockHeatmap' in css and '[data-theme="light"] .heatmapTile' in css and '@media(max-width:720px)' in css,
    'reduced motion supported': '@media(prefers-reduced-motion:reduce)' in css,
}
for name, ok in checks.items():
    print(('PASS' if ok else 'FAIL') + ' ' + name)
if not all(checks.values()):
    raise SystemExit(1)
print(f'{sum(checks.values())}/{len(checks)} checks passed')
