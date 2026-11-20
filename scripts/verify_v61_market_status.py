from pathlib import Path
root = Path(__file__).resolve().parents[1]
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
api = (root / 'services/api/app/main.py').read_text(encoding='utf-8')
checks = {
    'IST regular-session clock is timezone-aware': "timeZone:'Asia/Kolkata'" in app and 'getIndianSessionStatus(clockNow)' in app,
    'header clearly shows session status': 'marketSessionBadge' in app and 'Market closed · outside regular hours' in app,
    'closed-market quotes are not described as new live ticks': 'Market closed · last quote' in app and 'No new ticks expected outside regular hours.' in app,
    'date-only provider bars are parsed as IST calendar dates': 'T12:00:00+05:30' in app,
    'chart date labels use the selected candle interval': 'formatMarketTimestamp(t,interval)' in app,
    'latest provider candle timestamp is visible': 'latest bar '+"'"+'+formatMarketTimestamp(candleLastUpdated,chartInterval)' in app,
    'missing volume remains missing rather than becoming zero': ('Volume:read(b,' + "'Volume'" + ')==null?null:Number(read(b,' + "'Volume'" + '))' in app) and "current.Volume==null?'—'" in app,
    'session badge styles support both themes': '.marketSessionBadge' in css and '[data-theme="light"] .marketSessionBadge' in css,
    'historical freshness uses India calendar date': 'datetime.now(ZoneInfo("Asia/Kolkata")).date()' in api,
    'freshness note disclaims holiday/provider limitations': 'exchange holidays and provider delays can affect interpretation' in api,
}
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if not all(checks.values()):
    raise SystemExit(1)
print(f'{sum(checks.values())}/{len(checks)} V61 market-status checks passed')
