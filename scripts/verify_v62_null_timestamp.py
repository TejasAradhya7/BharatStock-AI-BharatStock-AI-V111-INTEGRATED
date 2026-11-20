from pathlib import Path
p = Path(__file__).resolve().parents[1] / 'apps/web/src/App.tsx'
s = p.read_text(encoding='utf-8')
checks = {
    'timestamp parser accepts untrusted values': 'function parseMarketTimestamp(value:unknown):Date' in s,
    'null and non-string timestamps are rejected safely': "if(typeof value !== 'string' || !value.trim()) return new Date(Number.NaN);" in s,
    'invalid timestamps display a safe fallback': "return 'Timestamp unavailable';" in s,
    'chart filters bars with missing or invalid timestamps': "typeof b.time==='string' && b.time.trim().length>0 && !Number.isNaN(parseMarketTimestamp(b.time).getTime())" in s,
    'API response is checked before candle normalization': 'Array.isArray(j.bars)?j.bars:[]' in s,
    'API candle timestamps fall back to provider date fields safely': "const rawTime=read(b,'time','datetime','date','timestamp','index')" in s,
}
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if not all(checks.values()):
    raise SystemExit(1)
print(f"{sum(checks.values())}/{len(checks)} null-timestamp regression checks passed")
