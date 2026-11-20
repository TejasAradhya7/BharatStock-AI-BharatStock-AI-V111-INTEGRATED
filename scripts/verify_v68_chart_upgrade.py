from pathlib import Path
root = Path(__file__).resolve().parents[1]
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
checks = {
    'chart supports real provider OHLC bars': 'type Candle = { time:string; Open:number; High:number; Low:number; Close:number; Volume:number|null }' in app,
    'candlestick and close-line views available': "useState<'candles'|'line'>('candles')" in app and "chartType==='line'" in app,
    'SMA 20 overlay available': "indicators.includes('SMA 20')" in app,
    'SMA 50 overlay available': "indicators.includes('SMA 50')" in app,
    'EMA 20 overlay available': "indicators.includes('EMA 20')" in app,
    'Bollinger Bands overlay available': "indicators.includes('Bollinger Bands')" in app,
    'visible candle range control available': 'chart-visible-bars' in app and 'All available' in app,
    'daily date-range control available': 'chart-period' in app and '5 years' in app,
    'indicator controls are interactive': 'chartIndicators.includes(name)' in app and 'setChartIndicators' in app,
    'responsive tool styling available': '.chartTools' in css and '@media(max-width:720px)' in css,
    'theme-aware chart tools available': '[data-theme="light"] .chartTools' in css,
    'real provider bars remain validated': 'setCandleBars(normalized)' in app and 'No sample candles are generated.' in app,
}
for name, ok in checks.items():
    print(('PASS' if ok else 'FAIL') + ': ' + name)
if not all(checks.values()):
    raise SystemExit(1)
print(f'PASS: {len(checks)}/{len(checks)} V68 chart upgrade checks')
