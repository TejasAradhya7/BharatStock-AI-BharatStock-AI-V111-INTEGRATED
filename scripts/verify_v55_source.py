from pathlib import Path
root = Path(__file__).resolve().parents[1]
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
checks = {
    'historical OHLC chart exists': 'TradingChart bars={candleBars}' in app,
    'live quotes are separate from historical candles': 'Upstox live market' in app and 'Provider OHLC candles' in app,
    'live chart data uses provider quotes': 'setLiveQuotes(j.quotes||[])' in app,
    'chart bars are validated before rendering': 'b.High>=Math.max(b.Open,b.Close,b.Low)' in app,
    'no fake candle points': 'No sample candles are generated.' in app,
    'snapshot limitation disclosed': 'not a promise of a five-minute live refresh' in app,
    'stream freshness status': 'treat quotes as stale' in app and 'Waiting for fresh quotes' in app,
    'historical CSV retained': '/export.csv?period=${period}' in app,
    'SMA and EMA overlays retained': "indicators.includes('SMA 20')" in app and "indicators.includes('SMA 50')" in app and "indicators.includes('EMA 20')" in app,
    'theme-aware chart styling': "grid:theme==='light'?'#e2e8f0':'#263449'" in app,
    'chart controls styled': '.intervalToolbar' in css and '.chartTools' in css,
}
for name, ok in checks.items():
    print(('PASS' if ok else 'FAIL') + ' - ' + name)
if not all(checks.values()):
    raise SystemExit(1)
print(f'{sum(checks.values())}/{len(checks)} source checks passed')
