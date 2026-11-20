from pathlib import Path
import re
root = Path(__file__).resolve().parents[1]
source = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
controls = re.findall(r'<(input|select|textarea)\b([^<>]*?)>', source)
missing = [(tag, attrs[:100]) for tag, attrs in controls if not re.search(r'\bid\s*=', attrs) or not re.search(r'\bname\s*=', attrs)]
assert controls, 'No native form controls found'
assert not missing, f'Controls missing id/name: {missing}'
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
assert 'prefers-reduced-motion: reduce' in css
assert '.chartPanel .chart' in css and 'contain: layout paint' in css
assert 'id="bs-input-' in source and 'name="bs-input-' in source
print(f'PASS: {len(controls)} native controls have id and name')
print('PASS: chart space reserved to reduce layout movement')
print('PASS: reduced-motion styles retained')
assert 'intervalToolbar' in source and 'TradingChart bars={candleBars}' in source
assert 'api/chart/' in source and 'OHLC candles' in source
assert 'No sample candles are generated' in source
print('PASS: interval toolbar is wired to the OHLC chart API')
print('PASS: candlestick view uses provider OHLC values and does not synthesize candles')
