from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = (root / "apps/web/src/App.tsx").read_text(encoding="utf-8")
css = (root / "apps/web/src/style.css").read_text(encoding="utf-8")
notes = (root / "RELEASE_NOTES-V75-PAPER-TRADING.md").read_text(encoding="utf-8")
checks = {
    "confidence gate": "confidence<0.6" in app and "Number(prediction.confidence)>=0.6" in app,
    "fresh symbol guard": "predictionSymbol!==symbol.toUpperCase()" in app,
    "virtual position entry": "openPaperTrade" in app and "status:'OPEN'" in app,
    "close and P/L tracking": "function closePaperTrade" in app and "function paperPnl" in app,
    "browser persistence": "bharatstock.paperTrades" in app,
    "simulator UI styles": ".paperTradePanel" in css and ".paperTradeTable" in css,
    "no-real-orders disclaimer": "No broker connection, real orders, or real money handling" in notes,
}
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if not all(checks.values()):
    raise SystemExit(1)
