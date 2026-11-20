from pathlib import Path
root = Path(__file__).resolve().parents[1]
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
checks = {
    'quote age refreshes without new packets': 'setInterval(()=>setClockNow(Date.now()),5000)' in app,
    'quote becomes stale after 30 seconds': 'liveTickAgeMs>30000' in app,
    'unknown timestamp is not presented as live': 'No quote timestamp received; live freshness is unknown.' in app,
    'stale quotes get explicit status': "liveUpdatedAt?'Stale quotes':'Waiting for fresh quotes'" in app,
    'green live status requires fresh quote': 'upstoxConfigured&&!liveTickIsStale&&liveQuotes.some(q=>q.available)' in app,
    'AI prediction uncertainty and baseline context': 'treat the result as weak evidence' in app and 'majority_baseline_accuracy' in app,
    'stress P/L uses displayed scenario values': '(Number(stressResult.scenario_price)-Number(stressResult.reference_price))*Number(stressResult.quantity)' in app,
    'stress result mismatch warning': 'The API P/L does not match the displayed reference price' in app,
    'zero-trade backtest explanation': 'No trades were generated in this period' in app,
    'missing indicators have explanations': 'Unavailable: need 50 valid closes' in app and 'Unavailable: insufficient history' in app,
    'browser-local alert limitation disclosed': 'They do not run server-side and cannot guarantee delivery.' in app,
    'no demo prices substituted': 'Data unavailable — no demo prices substituted' in app,
    'light-theme alert styles exist': '[data-theme="light"] .alertTriggered' in css and '[data-theme="light"] .alertDiagnostic' in css,
}
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
print(f"{sum(checks.values())}/{len(checks)} source checks passed")
raise SystemExit(0 if all(checks.values()) else 1)
