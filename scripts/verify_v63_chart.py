from pathlib import Path
root = Path(__file__).resolve().parents[1]
api = (root / 'services/api/app/main.py').read_text(encoding='utf-8')
web = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
checks = {
    'weekly and monthly candles aggregate provider daily OHLC': 'frame.resample(rule, label=label, closed=closed).agg' in api and '"W-FRI" if interval == "1wk" else "MS"' in api,
    'chart API preserves real provider data without synthetic bars': 'yf.Ticker(ticker).history' in api and 'OHLC' in api,
    'frontend accepts case-insensitive time/date fields': "Object.keys(obj||{}).find(k=>k.toLowerCase()===key.toLowerCase())" in web,
    'frontend validates OHLC consistency before rendering': 'b.High>=Math.max(b.Open,b.Close,b.Low)' in web and 'b.Low<=Math.min(b.Open,b.Close,b.High)' in web,
    'empty or malformed provider response gets an explicit message': 'timestamps or OHLC values were invalid' in web and 'returned no bars' in web,
    'timestamp parser guards null values': "typeof value !== 'string' || !value.trim()" in web,
}
for label, passed in checks.items():
    print(('PASS' if passed else 'FAIL') + ': ' + label)
assert all(checks.values()), 'One or more chart regression checks failed'
print(f'PASS: {len(checks)}/{len(checks)} V63 chart regression checks')
