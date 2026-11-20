from pathlib import Path
app = Path('apps/web/src/App.tsx').read_text()
checks = {
    'quote age updates every five seconds': 'setInterval(()=>setClockNow(Date.now()),5000)' in app,
    'stale threshold is 30 seconds': 'liveTickAgeMs>30000' in app,
    'unknown timestamp is not called live': 'No quote timestamp received; live freshness is unknown.' in app,
    'stale quote badge is explicit': "liveUpdatedAt?'Stale quotes':'Waiting for fresh quotes'" in app,
    'live badge is green only while fresh': 'upstoxConfigured&&!liveTickIsStale&&liveQuotes.some(q=>q.available)' in app,
    'existing AI uncertainty note remains': 'treat the result as weak evidence' in app,
    'stress P/L recalculated from displayed values': '(Number(stressResult.scenario_price)-Number(stressResult.reference_price))*Number(stressResult.quantity)' in app,
    'no-trade explanation remains': 'No trades were generated in this period' in app,
    'browser-local alert limitation disclosed': 'They do not run server-side and cannot guarantee delivery.' in app,
    'no demo prices fallback': 'Data unavailable — no demo prices substituted' in app,
}
for name, ok in checks.items(): print(('PASS' if ok else 'FAIL') + ': ' + name)
print(f'{sum(checks.values())}/{len(checks)} source checks passed')
raise SystemExit(0 if all(checks.values()) else 1)
