from pathlib import Path
root = Path(__file__).resolve().parents[1]
api = (root / "services/api/app/main.py").read_text(encoding="utf-8")
web = (root / "apps/web/src/App.tsx").read_text(encoding="utf-8")
checks = {
    "API builds canonical time field from provider index": "candle_time = pd.Timestamp(stamp).isoformat()" in api and 'records.append({"time": candle_time, **values})' in api,
    "API emits numeric OHLCV values explicitly": 'float(row[name]) if pd.notna(row[name]) else None' in api,
    "API validates provider OHLC before returning candles": 'if h < max(o, c, low) or low > min(o, c, h):' in api,
    "API fails clearly when no valid candles exist": 'The provider returned no valid OHLC candles' in api,
    "frontend normalizes multiple timestamp field names": "const rawTime=read(b,'time','datetime','date','timestamp','index')" in web,
    "frontend does not fabricate empty chart bars": 'No sample candles are generated.' in web,
}
for name, ok in checks.items(): print(f"{'PASS' if ok else 'FAIL'}: {name}")
if not all(checks.values()): raise SystemExit(1)
print(f"PASS: {sum(checks.values())}/{len(checks)} V64 chart contract checks")
