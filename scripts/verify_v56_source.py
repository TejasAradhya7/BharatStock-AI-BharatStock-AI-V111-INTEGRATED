from pathlib import Path
root = Path(__file__).resolve().parents[1]
analysis = (root / 'services/api/app/analysis.py').read_text()
app = (root / 'apps/web/src/App.tsx').read_text()
checks = {
 'baseline chosen from training labels only': 'baseline_class = int(y_train.value_counts().idxmax())' in analysis,
 'holdout baseline computed on test period': 'accuracy_score(y_test, np.full(len(y_test), baseline_class, dtype=int))' in analysis,
 'model confidence emitted': '"confidence": confidence' in analysis,
 'confidence band emitted': '"signal_quality": signal_quality' in analysis,
 'no 90 percent promise': 'A 90% success rate cannot be promised' in analysis,
 'UI displays model confidence carefully': 'Model confidence only, not probability of profit' in app,
 'UI avoids guarantee': 'A 90% success rate cannot be guaranteed' in app,
 'historical provider OHLC chart retained': 'TradingChart bars={candleBars}' in app,
 'no sample candles are generated': 'No sample candles are generated.' in app,
 'no-trade explanation retained': 'No trades were generated in this period' in app,
 'stress P/L recomputed from displayed values': '(stressResult.scenario_price-stressResult.reference_price)*stressResult.quantity' in app,
}
for name, ok in checks.items(): print(('PASS' if ok else 'FAIL') + ' ' + name)
raise SystemExit(0 if all(checks.values()) else 1)
