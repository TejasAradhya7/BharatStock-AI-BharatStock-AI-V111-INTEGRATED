from pathlib import Path
root = Path(__file__).resolve().parents[1]
app = (root / 'apps/web/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'apps/web/src/style.css').read_text(encoding='utf-8')
api = (root / 'services/api/app/main.py').read_text(encoding='utf-8')
models = (root / 'services/api/app/models.py').read_text(encoding='utf-8')
checks = {
    'stock heatmap present': 'Stock heatmap' in app and 'heatmapTile' in app,
    'selected stock analysis action present': 'generateSelectedIdea' in app and 'Analyze ${symbol}' in app,
    'both index suggestions generated': "['^NSEI','^BSESN']" in app,
    'persistent trade idea model exists': 'class TradeIdea(Base)' in models and '__tablename__ = "trade_ideas"' in models,
    'suggestion uses real historical provider data': 'fetch_history(normalized, "1y")' in api,
    'setup derives from SMA RSI ATR': all(term in api for term in ['SMA20', 'SMA50', 'latest_rsi', 'ATR-based']),
    'trade journal read endpoint exists': '@app.get("/api/trades")' in api,
    'trade status update endpoint exists': '@app.patch("/api/trades/{trade_id}")' in api,
    'frontend renders persistent journal': 'id="index-trade-dashboard"' in app and 'loadTradeIdeas' in app,
    'clear research-only disclaimer': 'not a guarantee' in api and 'not buy/sell orders' in app,
    'responsive themed journal styles': '.tradeJournal' in css and '[data-theme="light"] .tradeIdea' in css,
}
for label, passed in checks.items():
    print(('PASS' if passed else 'FAIL') + ' ' + label)
if not all(checks.values()):
    raise SystemExit(1)
print(f'{sum(checks.values())}/{len(checks)} checks passed')
