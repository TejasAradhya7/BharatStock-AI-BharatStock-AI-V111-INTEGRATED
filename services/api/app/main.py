from __future__ import annotations
import os
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .rate_limit import limiter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from .database import SessionLocal, init_db
from .models import AnalysisLog, TradeIdea, NewsEvent, ProspectivePrediction
from .schemas import SentimentRequest, NewsEventRequest
from .engine import sentiment_score
from .market import fetch_history, fetch_daily_history
from .analysis import predict
from .news import fetch_live_news_sentiment
from .real_world import (
    parse_iso_datetime,
    score_headline,
    fetch_upstox_intraday,
    fetch_upstox_historical,
    fetch_upstox_news,
    build_intraday_features,
    align_news_features,
    walk_forward_intraday,
    walk_forward_three_class_intraday,
)
from .upstox import get_live_quotes, live_provider_status, normalize_symbols
from .upstox_stream import stream_manager

# A per-process cap prevents a single API worker from accumulating unbounded
# dashboard WebSocket clients. Set MAX_LIVE_WS_CLIENTS to tune for deployment.
live_ws_clients: set[WebSocket] = set()

def max_live_ws_clients() -> int:
    try:
        return max(1, min(1000, int(os.getenv("MAX_LIVE_WS_CLIENTS", "100"))))
    except (TypeError, ValueError):
        return 100

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as exc:
        # App may still boot if DB is temporarily unavailable; health reports database state.
        app.state.db_startup_error = str(exc)
    stream_manager.start()
    yield
    stream_manager.stop()

app = FastAPI(title="BharatStock AI API", version="1.0.0", lifespan=lifespan,
              description="Research dashboard API. Predictions are experimental, not financial advice.")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST","PATCH"], allow_headers=["*"])


def _env_int(name: str, default: int, minimum: int = 1, maximum: int = 100000) -> int:
    try:
        return max(minimum, min(maximum, int(os.getenv(name, str(default)))))
    except (TypeError, ValueError):
        return default


class ExpensiveRouteRateLimitMiddleware(BaseHTTPMiddleware):
    """Bound upstream-data and model requests before they consume provider quota/CPU."""
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/live/quotes"):
            bucket, limit = "quotes", _env_int("RATE_LIMIT_QUOTES_PER_WINDOW", 60)
        elif path.startswith("/api/predict/") or path.startswith("/api/backtest/") or path.startswith("/api/research/intraday/"):
            bucket, limit = "analysis", _env_int("RATE_LIMIT_ANALYSIS_PER_WINDOW", 20)
        elif path.startswith("/api/market/") or path.startswith("/api/chart/") or path.startswith("/api/news/events"):
            bucket, limit = "history", _env_int("RATE_LIMIT_HISTORY_PER_WINDOW", 40)
        else:
            return await call_next(request)

        # Only trust forwarded client IP headers when explicitly enabled behind a
        # reverse proxy that overwrites these headers. Otherwise use ASGI peer IP.
        trust_proxy = os.getenv("TRUST_PROXY_HEADERS", "false").strip().lower() in {"1", "true", "yes", "on"}
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        real_ip = request.headers.get("x-real-ip", "").strip()
        if trust_proxy and (forwarded or real_ip):
            client_key = forwarded or real_ip
        else:
            client_key = request.client.host if request.client else "unknown"

        window = _env_int("RATE_LIMIT_WINDOW_SECONDS", 60, minimum=1, maximum=3600)
        allowed, retry_after = limiter.check(client_key, bucket, limit, window)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Request limit reached. Please retry after the indicated delay.",
                         "bucket": bucket, "retry_after_seconds": retry_after},
                headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
            )
        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(limit))
        response.headers.setdefault("X-RateLimit-Window", str(window))
        return response


app.add_middleware(ExpensiveRouteRateLimitMiddleware)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"name":"BharatStock AI API", "docs":"/docs", "health":"/health"}

@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Liveness check: report API health even if an optional dependency is down."""
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "unavailable"
    return {"status":"ok" if database == "connected" else "degraded", "database":database,
            "checked_at":datetime.now(timezone.utc).isoformat()}


@app.get("/api/system/status")
def system_status(db: Session = Depends(get_db)):
    """Return safe operational diagnostics without exposing credentials or environment values."""
    import importlib.util
    import platform

    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "unavailable"

    stream = stream_manager.status()
    token_configured = bool(os.getenv("UPSTOX_ACCESS_TOKEN", "").strip())
    dependencies = {
        name: importlib.util.find_spec(name) is not None
        for name in ("fastapi", "pandas", "numpy", "sklearn", "sqlalchemy")
    }
    return {
        "service": "BharatStock AI API",
        "api_version": app.version,
        "python_version": platform.python_version(),
        "database": database,
        "upstox": {
            "token_configured": token_configured,
            "stream_enabled": bool(stream.get("enabled", False)),
            "connection": stream.get("connection", "unknown"),
            "feed_health": stream.get("feed_health", "unknown"),
            "tick_age_seconds": stream.get("tick_age_seconds"),
        },
        "dependencies": dependencies,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "security_note": "Credentials and environment values are intentionally omitted.",
    }


@app.get("/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness check for deploys: summarize database and live-feed readiness."""
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "unavailable"
    stream = stream_manager.status()
    upstox_configured = bool(os.getenv("UPSTOX_ACCESS_TOKEN", "").strip())
    stream_required = os.getenv("UPSTOX_STREAM_REQUIRED", "false").strip().lower() in {"1", "true", "yes", "on"}
    stream_ready = stream.get("feed_health") == "live"
    # A quote token is optional for deployments that intentionally run research-only
    # endpoints. Require credentials and a fresh tick only when streaming is mandatory.
    ready = database == "connected" and (
        (upstox_configured and stream.get("enabled", False) and stream_ready)
        if stream_required else True
    )
    payload = {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "database": database,
            "upstox_token_configured": upstox_configured,
            "stream_enabled": stream.get("enabled", False),
            "stream_connection": stream.get("connection"),
            "feed_health": stream.get("feed_health"),
            "tick_age_seconds": stream.get("tick_age_seconds"),
            "stream_required_for_readiness": stream_required,
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)

@app.get("/api/symbols")
def symbols():
    """Return a curated starter watchlist of common Indian-market tickers."""
    return {
        "symbols": [
            {"symbol": "^NSEI", "name": "NIFTY 50", "kind": "Index"},
            {"symbol": "^BSESN", "name": "SENSEX", "kind": "Index"},
            {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "kind": "Equity"},
            {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "kind": "Equity"},
            {"symbol": "INFY.NS", "name": "Infosys", "kind": "Equity"},
            {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "kind": "Equity"},
            {"symbol": "ICICIBANK.NS", "name": "ICICI Bank", "kind": "Equity"},
            {"symbol": "SBIN.NS", "name": "State Bank of India", "kind": "Equity"},
        ],
        "note": "Starter watchlist only. Provider ticker coverage and market-data availability can vary.",
    }


@app.get("/api/analysis/correlation")
def correlation_analysis(
    symbols: str = Query(..., min_length=3, max_length=240),
    period: str = Query("1y", pattern="^(3mo|6mo|1y|2y|5y)$"),
):
    """Calculate pairwise correlations of aligned daily close-to-close returns."""
    import pandas as pd

    requested = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    # Preserve order while removing duplicate tickers.
    requested = list(dict.fromkeys(requested))
    if len(requested) < 2 or len(requested) > 8:
        raise HTTPException(status_code=422, detail="Provide between 2 and 8 distinct ticker symbols.")

    returns: dict[str, pd.Series] = {}
    try:
        for ticker in requested:
            history = fetch_history(ticker, period)
            if "Close" not in history.columns:
                raise HTTPException(status_code=422, detail=f"No closing-price series available for {ticker}.")
            close = pd.to_numeric(history["Close"], errors="coerce")
            close = close[close > 0].dropna()
            daily = close.pct_change().replace([float("inf"), float("-inf")], pd.NA).dropna()
            if len(daily) < 20:
                raise HTTPException(status_code=422, detail=f"At least 20 daily returns are required for {ticker}.")
            returns[ticker] = daily
    except HTTPException:
        raise
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Correlation data provider failed: {type(exc).__name__}. Try again later.")

    aligned = pd.DataFrame(returns).dropna(how="any")
    if len(aligned) < 20:
        raise HTTPException(status_code=422, detail="The selected tickers have fewer than 20 overlapping daily returns.")
    matrix = aligned.corr(method="pearson")
    return {
        "period": period,
        "symbols": requested,
        "observations": int(len(aligned)),
        "method": "Pearson correlation of aligned daily close-to-close percentage returns",
        "matrix": [
            {"symbol": ticker, **{other: round(float(matrix.loc[ticker, other]), 4) for other in requested}}
            for ticker in requested
        ],
        "disclaimer": "Historical correlation is not causal evidence and can change sharply during market stress.",
    }


@app.get("/api/chart/{symbol}")
def chart_data(
    symbol: str,
    interval: str = Query("1d", pattern="^(5m|10m|15m|30m|1h|4h|1d|1wk|1mo)$"),
    period: str | None = Query(None),
):
    """Return real provider OHLCV bars for the selected chart interval; never synthesize candles."""
    import pandas as pd
    from .market import validate_symbol, fetch_daily_history
    try:
        ticker = symbol.strip().upper()
        # Reuse the same strict ticker validation as the main history loader.
        validate_symbol(ticker)

        if interval in {"5m", "10m", "15m", "30m", "1h", "4h"}:
            chosen_period = period or ("5d" if interval in {"5m", "10m", "15m"} else "1mo")
            if chosen_period not in {"1d", "5d", "1mo", "3mo", "6mo"}:
                raise HTTPException(status_code=422, detail="Intraday charts support 1 day, 5 days, 1 month, or 3 months depending on provider limits.")
            provider_interval = "5m" if interval in {"5m", "10m"} else "60m" if interval in {"1h", "4h"} else interval

            import yfinance as yf

            frame = yf.Ticker(ticker).history(
                period=chosen_period,
                interval=provider_interval,
                auto_adjust=True,
            )
            if frame is None or frame.empty:
                raise LookupError("No intraday bars returned by the market-data provider for this symbol and interval.")
            frame = frame.rename(columns={c: c.title() for c in frame.columns})
            frame = frame[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Open", "High", "Low", "Close"])
            if interval in {"10m", "4h"}:
                rule = "10min" if interval == "10m" else "4h"
                frame = frame.resample(rule, origin="start_day", label="left", closed="left").agg({"Open":"first", "High":"max", "Low":"min", "Close":"last", "Volume":"sum"}).dropna(subset=["Open", "High", "Low", "Close"])
        else:
            chosen_period = period or ("1y" if interval == "1d" else "5y")
            if chosen_period not in {"1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}:
                raise HTTPException(status_code=422, detail="Daily, weekly and monthly charts support 1 month to maximum history.")
            # Use provider daily OHLC as the canonical source, then aggregate weekly/monthly
            # bars locally. Yahoo's native 1wk/1mo endpoints can intermittently return empty
            # frames even while daily history is available. Aggregation preserves real OHLC.
            provider_interval = "1d" if interval in {"1wk", "1mo"} else "1d"
            frame = fetch_daily_history(ticker, chosen_period)
            if frame is None or frame.empty:
                raise LookupError("No historical bars returned by the market-data provider for this symbol and interval.")
            frame = frame.rename(columns={c: c.title() for c in frame.columns})
            frame = frame[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Open", "High", "Low", "Close"])
            if interval in {"1wk", "1mo"}:
                # Weekly candles start Monday; monthly candles start on the first calendar day.
                rule = "W-FRI" if interval == "1wk" else "MS"
                label = "right" if interval == "1wk" else "left"
                closed = "right" if interval == "1wk" else "left"
                frame = frame.resample(rule, label=label, closed=closed).agg(
                    {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
                ).dropna(subset=["Open", "High", "Low", "Close"])
        if frame.empty:
            raise LookupError("No complete OHLC bars are available for this selection.")
        # Build an explicit JSON contract rather than relying on pandas reset_index()
        # column names (Date/Datetime/index vary by provider/version). This was the
        # failure-prone path behind a chart showing a latest date but zero valid bars.
        frame.index = pd.to_datetime(frame.index)
        frame = frame.sort_index()
        records = []
        for stamp, row in frame.tail(500).iterrows():
            try:
                candle_time = pd.Timestamp(stamp).isoformat()
                values = {name: float(row[name]) if pd.notna(row[name]) else None
                          for name in ("Open", "High", "Low", "Close", "Volume")}
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
            if not candle_time or any(values[name] is None for name in ("Open", "High", "Low", "Close")):
                continue
            o, h, low, c = (values[name] for name in ("Open", "High", "Low", "Close"))
            if not all(map(lambda n: n == n and abs(n) != float("inf"), (o, h, low, c))):
                continue
            if h < max(o, c, low) or low > min(o, c, h):
                continue
            records.append({"time": candle_time, **values})
        if not records:
            raise LookupError("The provider returned no valid OHLC candles for this symbol and interval.")
        return {"symbol": ticker, "interval": interval, "period": chosen_period,
                "source": "Yahoo Finance via yfinance (delayed/availability varies)",
                "last_updated": records[-1]["time"], "count": len(records), "bars": records,
                "note": "OHLCV bars are provider history, not guaranteed exchange tick-by-tick data. The newest candle may be incomplete."}
    except HTTPException:
        raise
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chart data provider failed: {type(exc).__name__}. Try another interval or symbol later.")


@app.get("/api/market/{symbol}")
def market(symbol: str, period: str = Query("1y", pattern="^(1mo|3mo|6mo|1y|2y|5y|max)$")):
    try:
        df = fetch_history(symbol, period)
        out = df.reset_index()
        date_col = "Date" if "Date" in out.columns else out.columns[0]
        out[date_col] = out[date_col].astype(str)
        # Normalize NaN/NaT to JSON null before handing rows to FastAPI.
        out = out.astype(object).where(out.notna(), None)
        rows = out.tail(400).to_dict(orient="records")
        # Surface data freshness explicitly. Calendar-day age is only a heuristic:
        # weekends and exchange holidays can make a valid market session look older.
        latest_timestamp = df.index[-1]
        latest_date = latest_timestamp.date() if hasattr(latest_timestamp, "date") else latest_timestamp
        today_ist = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        age_days = max(0, (today_ist - latest_date).days)
        if age_days <= 4:
            freshness = "recent"
        elif age_days <= 10:
            freshness = "check_exchange_calendar"
        else:
            freshness = "possibly_stale"
        return {"symbol":symbol.upper(), "period":period, "source":"Yahoo Finance via yfinance (delayed/availability varies)",
                "last_updated":str(df.index[-1]),
                "data_quality":{"rows_returned":len(rows), "latest_session_date":str(latest_date),
                                "calendar_days_since_latest":age_days, "freshness":freshness,
                                "freshness_note":"Calendar-day heuristic calculated using the India calendar date; weekends, exchange holidays and provider delays can affect interpretation. This is not a live-quote guarantee."},
                "rows":rows}
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Market data provider failed: {type(exc).__name__}. Try again later.")


@app.get("/api/market/{symbol}/export.csv")
def export_market_csv(symbol: str, period: str = Query("1y", pattern="^(1mo|3mo|6mo|1y|2y|5y|max)$")):
    """Export historical prices and technical indicators as a downloadable CSV."""
    import io
    try:
        df = fetch_history(symbol, period).copy()
        output = io.StringIO()
        export_frame = df.reset_index()
        date_column = "Date" if "Date" in export_frame.columns else export_frame.columns[0]
        export_frame[date_column] = export_frame[date_column].astype(str)
        export_frame.to_csv(output, index=False, na_rep="")
        safe_symbol = "".join(ch for ch in symbol.upper() if ch.isalnum() or ch in "._-^")[:24] or "market"
        return Response(
            content=output.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_symbol}-{period}-history.csv"',
                     "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Market export failed: {type(exc).__name__}. Check market-data availability.")


@app.get("/api/position-size")
def position_size(
    portfolio_value: float = Query(..., gt=0, le=1_000_000_000),
    risk_percent: float = Query(1.0, gt=0, le=5),
    entry_price: float = Query(..., gt=0, le=100_000_000),
    stop_price: float = Query(..., gt=0, le=100_000_000),
    max_allocation_percent: float = Query(20.0, gt=0, le=100),
):
    """Educational long-position sizing calculator; never places orders."""
    import math
    if stop_price >= entry_price:
        raise HTTPException(status_code=422, detail="For a long position, stop_price must be below entry_price.")
    risk_per_share = entry_price - stop_price
    risk_budget = portfolio_value * risk_percent / 100.0
    allocation_cap = portfolio_value * max_allocation_percent / 100.0
    shares_by_risk = math.floor(risk_budget / risk_per_share)
    shares_by_allocation = math.floor(allocation_cap / entry_price)
    shares = max(0, min(shares_by_risk, shares_by_allocation))
    capital_required = shares * entry_price
    planned_loss = shares * risk_per_share
    return {
        "portfolio_value": round(portfolio_value, 2),
        "risk_percent": risk_percent,
        "risk_budget": round(risk_budget, 2),
        "entry_price": round(entry_price, 2),
        "stop_price": round(stop_price, 2),
        "risk_per_share": round(risk_per_share, 2),
        "max_allocation_percent": max_allocation_percent,
        "allocation_cap": round(allocation_cap, 2),
        "shares_by_risk_limit": shares_by_risk,
        "shares_by_allocation_limit": shares_by_allocation,
        "recommended_quantity_for_plan": shares,
        "capital_required": round(capital_required, 2),
        "planned_loss_at_stop": round(planned_loss, 2),
        "portfolio_risk_at_stop_pct": round(planned_loss / portfolio_value * 100.0, 4),
        "assumptions": ["Long position only", "Stop executes at the specified price", "Excludes brokerage, taxes, slippage, gaps and liquidity risk", "Calculation is educational and does not recommend a trade"],
    }


@app.get("/api/stress/{symbol}")
def scenario_stress(
    symbol: str,
    shock_pct: float = Query(-10.0, ge=-100, le=100, description="Hypothetical price change percentage"),
    quantity: int = Query(1, ge=0, le=1_000_000_000),
    period: str = Query("1y", pattern="^(3mo|6mo|1y|2y|5y)$"),
):
    """Apply a hypothetical price shock to a share quantity; this is not a forecast."""
    import pandas as pd
    try:
        frame = fetch_history(symbol, period)
        if "Close" not in frame or frame.empty:
            raise LookupError("Historical closing prices are unavailable for this symbol.")
        closes = pd.to_numeric(frame["Close"], errors="coerce").dropna()
        if closes.empty:
            raise LookupError("No valid closing price is available for this symbol.")
        current_price = float(closes.iloc[-1])
        if not (current_price > 0 and current_price < float("inf")):
            raise LookupError("The latest closing price is invalid.")
        shocked_price = current_price * (1.0 + shock_pct / 100.0)
        position_value = current_price * quantity
        shocked_value = shocked_price * quantity
        pnl = shocked_value - position_value
        return {
            "symbol": symbol.upper(), "period": period, "quantity": quantity,
            "reference_price": round(current_price, 4), "shock_pct": shock_pct,
            "scenario_price": round(shocked_price, 4),
            "current_position_value": round(position_value, 2),
            "scenario_position_value": round(shocked_value, 2),
            "profit_loss": round(pnl, 2),
            "method": "Linear hypothetical shock applied to the latest historical close; excludes dividends and trading costs",
            "disclaimer": "Scenario only, not a forecast, stop guarantee, or investment recommendation.",
        }
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scenario stress analysis failed: {type(exc).__name__}. Check market-data availability.")


@app.get("/api/risk/{symbol}")
def risk_analytics(symbol: str, period: str = Query("1y", pattern="^(3mo|6mo|1y|2y|5y)$")):
    """Historical daily-return risk summary. Estimates are not forecasts or guarantees."""
    import numpy as np
    import pandas as pd

    try:
        df = fetch_history(symbol, period).copy()
        if "Close" not in df or len(df) < 30:
            raise LookupError("At least 30 closing-price observations are required for risk analytics.")
        close = pd.to_numeric(df["Close"], errors="coerce")
        returns = close.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        returns = returns[np.isfinite(returns)]
        if len(returns) < 20:
            raise LookupError("At least 20 valid daily returns are required for risk analytics.")
        var95 = float(np.quantile(returns, 0.05))
        var99 = float(np.quantile(returns, 0.01))
        tail95 = returns[returns <= var95]
        tail99 = returns[returns <= var99]
        annualized_vol = float(returns.std(ddof=1) * np.sqrt(252)) if len(returns) > 1 else 0.0
        downside = returns[returns < 0]
        downside_vol = float(downside.std(ddof=1) * np.sqrt(252)) if len(downside) > 1 else 0.0
        curve = (1.0 + returns).cumprod()
        drawdown = curve / curve.cummax() - 1.0
        return {
            "symbol": symbol.upper(), "period": period, "observations": int(len(returns)),
            "daily_var_95_pct": round(var95 * 100, 4),
            "daily_cvar_95_pct": round(float(tail95.mean()) * 100, 4),
            "daily_var_99_pct": round(var99 * 100, 4),
            "daily_cvar_99_pct": round(float(tail99.mean()) * 100, 4),
            "annualized_volatility_pct": round(annualized_vol * 100, 4),
            "annualized_downside_volatility_pct": round(downside_vol * 100, 4),
            "historical_max_drawdown_pct": round(float(drawdown.min()) * 100, 4),
            "method": "Historical daily close-to-close returns; empirical quantiles; 252 trading days per year",
            "assumptions": ["Historical estimates only", "Excludes fees, taxes, slippage and liquidity effects", "Not a forecast or investment recommendation"],
        }
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Risk analytics could not be completed: {type(exc).__name__}. Check market-data availability.")


@app.get("/api/risk/{symbol}/export.csv")
def export_risk_csv(symbol: str, period: str = Query("1y", pattern="^(3mo|6mo|1y|2y|5y)$")):
    """Export the same historical risk summary shown by the dashboard as a one-row CSV."""
    import csv
    import io

    result = risk_analytics(symbol, period)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=[
        "symbol", "period", "observations", "daily_var_95_pct", "daily_cvar_95_pct",
        "daily_var_99_pct", "daily_cvar_99_pct", "annualized_volatility_pct",
        "annualized_downside_volatility_pct", "historical_max_drawdown_pct", "method", "assumptions",
    ])
    writer.writeheader()
    row = dict(result)
    row["assumptions"] = "; ".join(row.get("assumptions", []))
    writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
    safe_symbol = "".join(ch for ch in symbol.upper() if ch.isalnum() or ch in "._-^")[:24] or "market"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_symbol}-{period}-risk.csv"',
                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@app.get("/api/backtest/{symbol}")
def backtest(symbol: str, period: str = Query("1y", pattern="^(3mo|6mo|1y|2y|5y)$"),
             cost_bps: float = Query(10.0, ge=0, le=100, description="Estimated one-way transaction cost in basis points")):
    """Educational SMA crossover backtest with one-bar execution lag. Excludes fees, tax and slippage."""
    import numpy as np
    import pandas as pd

    try:
        df = fetch_history(symbol, period).copy()
        if len(df) < 60:
            raise LookupError("At least 60 clean observations are required for this backtest.")
        close = pd.to_numeric(df["Close"], errors="coerce")
        sma20 = pd.to_numeric(df["SMA20"], errors="coerce")
        sma50 = pd.to_numeric(df["SMA50"], errors="coerce")
        daily_returns = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
        # Signal is shifted one observation so today's close is not used to earn today's return.
        position = (sma20 > sma50).shift(1).astype("boolean").fillna(False).astype(float)
        gross_strategy_returns = (daily_returns * position).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        # Charge estimated one-way costs on entries and exits. Position is already lagged,
        # so the fee is applied when the held position changes, not to the signal bar.
        position_changes = position.diff().abs()
        if len(position_changes):
            position_changes.iloc[0] = abs(float(position.iloc[0]))
        turnover_events = position_changes.fillna(0.0)
        estimated_cost_returns = turnover_events * (cost_bps / 10000.0)
        strategy_returns = (gross_strategy_returns - estimated_cost_returns).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        strategy_curve = (1.0 + strategy_returns).cumprod()
        gross_strategy_curve = (1.0 + gross_strategy_returns).cumprod()
        buy_hold_curve = (1.0 + daily_returns).cumprod()
        drawdown = strategy_curve / strategy_curve.cummax() - 1.0
        daily_vol = float(strategy_returns.std(ddof=1)) if len(strategy_returns) > 1 else 0.0
        sharpe = float((strategy_returns.mean() / daily_vol) * np.sqrt(252)) if daily_vol > 0 else None
        negative_returns = strategy_returns[strategy_returns < 0]
        downside_deviation = float(np.sqrt(np.mean(np.square(negative_returns)))) if len(negative_returns) else 0.0
        sortino = float((strategy_returns.mean() / downside_deviation) * np.sqrt(252)) if downside_deviation > 0 else None
        total_return = float(strategy_curve.iloc[-1]) - 1.0
        gross_total_return = float(gross_strategy_curve.iloc[-1]) - 1.0
        estimated_total_cost_pct = float(estimated_cost_returns.sum()) * 100.0
        years = max(len(strategy_returns) / 252.0, 1.0 / 252.0)
        annualized_return = float(strategy_curve.iloc[-1] ** (1.0 / years) - 1.0) if strategy_curve.iloc[-1] > 0 else -1.0
        max_drawdown = float(drawdown.min())
        calmar = float(annualized_return / abs(max_drawdown)) if max_drawdown < 0 else None
        market_exposure = float((position > 0).mean() * 100.0)
        entries = int(((position > 0) & (position.shift(1).fillna(0) <= 0)).sum())
        # Compare several pre-defined strategies on the same historical window.
        # All signals are shifted by one bar to avoid earning returns on the signal bar.
        strategy_comparison = []
        for short_window, long_window in ((5, 20), (10, 30), (20, 50), (50, 100)):
            if len(close) <= long_window + 5:
                continue
            short_sma = close.rolling(short_window, min_periods=short_window).mean()
            long_sma = close.rolling(long_window, min_periods=long_window).mean()
            held = (short_sma > long_sma).shift(1).astype("boolean").fillna(False).astype(float)
            gross = daily_returns * held
            changes = held.diff().abs()
            if len(changes):
                changes.iloc[0] = abs(float(held.iloc[0]))
            fees = changes.fillna(0.0) * (cost_bps / 10000.0)
            net = (gross - fees).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            curve = (1.0 + net).cumprod()
            dd = curve / curve.cummax() - 1.0
            vol = float(net.std(ddof=1)) if len(net) > 1 else 0.0
            ratio = float(net.mean() / vol * np.sqrt(252)) if vol > 0 else None
            strategy_comparison.append({
                "name": f"SMA {short_window}/{long_window}",
                "return_pct": round((float(curve.iloc[-1]) - 1.0) * 100, 3),
                "max_drawdown_pct": round(float(dd.min()) * 100, 3),
                "sharpe_ratio": round(ratio, 3) if ratio is not None else None,
                "exposure_pct": round(float((held > 0).mean()) * 100, 2),
                "trade_events": int((changes.fillna(0.0) > 0).sum()),
            })
        strategy_comparison.append({
            "name": "Buy & hold (benchmark)",
            "return_pct": round((float(buy_hold_curve.iloc[-1]) - 1.0) * 100, 3),
            "max_drawdown_pct": round(float((buy_hold_curve / buy_hold_curve.cummax() - 1.0).min()) * 100, 3),
            "sharpe_ratio": None,
            "exposure_pct": 100.0,
            "trade_events": 1,
        })
        return {
            "symbol": symbol.upper(), "period": period, "observations": int(len(df)),
            "strategy": "SMA20/SMA50 crossover; position delayed one session",
            "strategy_return_pct": round(total_return * 100, 3),
            "gross_strategy_return_pct": round(gross_total_return * 100, 3),
            "estimated_transaction_cost_pct": round(estimated_total_cost_pct, 4),
            "cost_bps_one_way": float(cost_bps),
            "turnover_events": int((turnover_events > 0).sum()),
            "annualized_return_pct": round(annualized_return * 100, 3),
            "buy_hold_return_pct": round((float(buy_hold_curve.iloc[-1]) - 1.0) * 100, 3),
            "max_drawdown_pct": round(max_drawdown * 100, 3),
            "annualized_volatility_pct": round(daily_vol * np.sqrt(252) * 100, 3),
            "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
            "sortino_ratio": round(sortino, 3) if sortino is not None else None,
            "calmar_ratio": round(calmar, 3) if calmar is not None else None,
            "market_exposure_pct": round(market_exposure, 2),
            "position_entries": entries,
            "strategy_comparison": strategy_comparison,
            "comparison_note": "Strategies use the same price window, one-bar signal delay and estimated transaction costs. This is an in-sample historical comparison, not a guarantee of future performance.",
            "assumptions": ["Historical adjusted closes", f"Estimated one-way transaction cost of {cost_bps:g} basis points per entry/exit event", "Cost estimate is a simplified model and excludes brokerage, taxes, slippage, market impact and minimum charges", "Not a forecast or investment recommendation"],
        }
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Backtest could not be completed: {type(exc).__name__}. Check market-data availability.")


INDEX_TRADE_SYMBOLS = {"^NSEI": "NIFTY 50", "^BSESN": "SENSEX"}

def _trade_idea_json(item: TradeIdea) -> dict:
    index_ranges = {"^NSEI": (1000.0, 100000.0), "^BSESN": (5000.0, 200000.0)}
    price = float(item.entry_price) if item.entry_price is not None else None
    limits = index_ranges.get(item.symbol)
    data_quality = "OK"
    if limits and (price is None or not limits[0] <= price <= limits[1]):
        data_quality = "INVALID_INDEX_PRICE"
    return {"id": item.id, "symbol": item.symbol, "index_name": INDEX_TRADE_SYMBOLS.get(item.symbol, item.symbol),
            "signal": item.signal, "status": item.status, "entry_price": item.entry_price,
            "stop_price": item.stop_price, "target_price": item.target_price, "latest_rsi": item.latest_rsi,
            "rationale": item.rationale, "created_at": item.created_at.isoformat() + "Z",
            "data_quality": data_quality,
            "data_quality_note": "Stored index price is outside the expected scale; do not use this record. Re-run analysis after correcting provider mapping." if data_quality != "OK" else None}

@app.get("/api/trades")
def list_trade_ideas(symbol: str | None = None, status: str | None = Query(None, pattern="^(watching|closed|ignored)$"),
                     limit: int = Query(100, ge=1, le=300), db: Session = Depends(get_db)):
    """Return persisted research ideas for the index-trade dashboard."""
    query = db.query(TradeIdea)
    # Keep malformed legacy index records in the database for auditability,
    # but never surface them as usable journal entries. They can be inspected
    # separately through database/admin tooling if required.
    query = query.filter(or_(
        TradeIdea.symbol != "^NSEI",
        and_(TradeIdea.entry_price >= 1000.0, TradeIdea.entry_price <= 100000.0),
    )).filter(or_(
        TradeIdea.symbol != "^BSESN",
        and_(TradeIdea.entry_price >= 5000.0, TradeIdea.entry_price <= 200000.0),
    ))
    if symbol:
        try:
            normalized = symbol.strip().upper()
            from .market import validate_symbol
            normalized = validate_symbol(normalized)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        query = query.filter(TradeIdea.symbol == normalized)
    if status:
        query = query.filter(TradeIdea.status == status)
    return [_trade_idea_json(item) for item in query.order_by(TradeIdea.created_at.desc()).limit(limit).all()]

@app.post("/api/trades/suggest/{symbol}")
def create_trade_idea(symbol: str, db: Session = Depends(get_db)):
    """Create a saved, rules-based watch setup from provider history; never places orders."""
    import math
    try:
        from .market import validate_symbol
        normalized = validate_symbol(symbol)
        frame = fetch_history(normalized, "1y").copy()
        if len(frame) < 60:
            raise LookupError("At least 60 provider-backed daily observations are required to evaluate an index setup.")
        last = frame.iloc[-1]
        close = float(last["Close"]); sma20 = float(last["SMA20"]); sma50 = float(last["SMA50"]); rsi = float(last["RSI"]); atr = float(last["ATR"])
        if not all(math.isfinite(v) for v in (close, sma20, sma50, rsi)) or close <= 0:
            raise LookupError("The latest provider row does not contain valid close, SMA20, SMA50 and RSI values.")
        # Catch wrong instrument mappings / malformed provider responses before
        # saving a misleading index-level setup (e.g. NIFTY shown near ₹139).
        expected_ranges = {"^NSEI": (1000.0, 100000.0), "^BSESN": (5000.0, 200000.0)}
        if normalized in expected_ranges:
            lower, upper = expected_ranges[normalized]
            if not lower <= close <= upper:
                raise LookupError(
                    f"Provider returned {normalized} close {close:.2f}, outside the sanity range "
                    f"{lower:.0f}–{upper:.0f}. No research idea was saved; verify ticker/instrument mapping."
                )
        atr = atr if math.isfinite(atr) and atr > 0 else close * 0.01
        if close > sma20 > sma50 and 50 <= rsi < 68:
            signal = "BULLISH_WATCH"
            stop = round(close - 1.5 * atr, 2); target = round(close + 3.0 * atr, 2)
            rationale = f"Close is above SMA20 ({sma20:.2f}), SMA20 is above SMA50 ({sma50:.2f}), and RSI is {rsi:.1f}; trend alignment is bullish. Stop/target are ATR-based research levels, not guaranteed execution prices."
        elif close < sma20 < sma50 and 32 < rsi <= 50:
            signal = "BEARISH_WATCH"
            stop = round(close + 1.5 * atr, 2); target = round(max(0.01, close - 3.0 * atr), 2)
            rationale = f"Close is below SMA20 ({sma20:.2f}), SMA20 is below SMA50 ({sma50:.2f}), and RSI is {rsi:.1f}; trend alignment is bearish. This is a watch signal, not a short-selling instruction."
        else:
            signal = "NO_CLEAR_SETUP"; stop = None; target = None
            rationale = f"No aligned setup: close {close:.2f}, SMA20 {sma20:.2f}, SMA50 {sma50:.2f}, RSI {rsi:.1f}. Wait for clearer conditions rather than forcing a trade."
        # Keep one current active watch per symbol. Re-running analysis refreshes
        # that watch instead of flooding the journal with identical active cards.
        # Closed/ignored rows remain as historical research records.
        item = (db.query(TradeIdea)
                .filter(TradeIdea.symbol == normalized, TradeIdea.status == "watching")
                .order_by(TradeIdea.created_at.desc())
                .first())
        if item is None:
            item = TradeIdea(symbol=normalized, signal=signal, status="watching", entry_price=round(close, 2),
                             stop_price=stop, target_price=target, latest_rsi=round(rsi, 2), rationale=rationale)
            db.add(item)
        else:
            item.signal = signal
            item.entry_price = round(close, 2)
            item.stop_price = stop
            item.target_price = target
            item.latest_rsi = round(rsi, 2)
            item.rationale = rationale
            item.created_at = datetime.utcnow()
        db.commit(); db.refresh(item)
        return {**_trade_idea_json(item), "source": "Yahoo Finance historical daily OHLCV",
                "observations": int(len(frame)), "method": "SMA20/SMA50 trend alignment + RSI; ATR-based illustrative risk levels",
                "disclaimer": "Research-only idea generated from delayed/provider historical data. Not personalized financial advice, not a live order, and not a guarantee. Verify current quotes, costs, liquidity and risk before acting."}
    except HTTPException:
        db.rollback(); raise
    except (ValueError, LookupError) as exc:
        db.rollback(); raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=502, detail=f"Could not generate a provider-backed setup: {type(exc).__name__}. Check market-data availability.")

@app.patch("/api/trades/{trade_id}")
def update_trade_idea(trade_id: int, status: str = Query(..., pattern="^(watching|closed|ignored)$"), db: Session = Depends(get_db)):
    """Update the journal status only; does not record a fill or calculate P/L."""
    item = db.query(TradeIdea).filter(TradeIdea.id == trade_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Trade idea not found.")
    item.status = status
    db.commit(); db.refresh(item)
    return _trade_idea_json(item)

@app.get("/api/live/status")
def live_status():
    """Report REST and WebSocket Upstox configuration without exposing credentials."""
    status = live_provider_status()
    status["stream"] = stream_manager.status()
    status["websocket_clients"] = len(live_ws_clients)
    status["websocket_client_limit"] = max_live_ws_clients()
    if status["stream"].get("feed_health") == "live":
        status["mode"] = "websocket_ltpc"
    elif status["configured"]:
        status["mode"] = "rest_snapshot_fallback"
    else:
        status["mode"] = "not_configured"
    return status


@app.get("/api/live/quotes")
def live_quotes(symbols: str = Query("RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS", min_length=1, max_length=600)):
    """Fetch current Upstox LTP snapshots. Clients may poll this endpoint for live dashboard refreshes."""
    try:
        requested = normalize_symbols(symbols)
        return get_live_quotes(requested)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstox quote request failed: {type(exc).__name__}.")


@app.websocket("/api/live/stream")
async def live_stream(websocket: WebSocket):
    """Push tick updates with a heartbeat and enforce a per-process client cap."""
    import asyncio

    await websocket.accept()
    limit = max_live_ws_clients()
    if len(live_ws_clients) >= limit:
        # 1013 tells the client the service is temporarily overloaded and that
        # reconnecting later may succeed. Clients already connected are unaffected.
        await websocket.close(code=1013, reason="Live stream client limit reached; retry later.")
        return

    live_ws_clients.add(websocket)
    last_sequence = -1
    last_state = None
    last_sent_at = 0.0
    try:
        while True:
            snapshot = stream_manager.snapshot()
            state = snapshot.get("connection")
            sequence = snapshot.get("sequence", 0)
            now = asyncio.get_running_loop().time()
            # A heartbeat keeps idle-market connections observable without sending
            # four identical frames per second to every connected dashboard.
            if sequence != last_sequence or state != last_state or now - last_sent_at >= 15:
                snapshot["server_time"] = datetime.now(timezone.utc).isoformat()
                snapshot["websocket_clients"] = len(live_ws_clients)
                await websocket.send_json(snapshot)
                last_sequence, last_state, last_sent_at = sequence, state, now
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        live_ws_clients.discard(websocket)


@app.post("/api/sentiment")
def sentiment(body: SentimentRequest):
    score, label = sentiment_score(body.text)
    return {"score":score, "label":label, "text":body.text,
            "note":"Lexicon-based headline sentiment; not a complete financial-language model."}

@app.post("/api/news/events")
def ingest_news_event(body: NewsEventRequest, db: Session = Depends(get_db)):
    """Store timestamped news/event evidence with a conservative availability time.

    The server ingestion time is always part of availability_at, preventing a
    backfilled headline from being treated as known before it entered this system.
    """
    from urllib.parse import urlparse
    try:
        symbol = body.symbol.strip().upper()
        if not symbol or len(symbol) > 32 or not all(ch.isalnum() or ch in "^._-|=" for ch in symbol):
            raise ValueError("Enter a valid symbol or Upstox instrument key.")
        published = parse_iso_datetime(body.published_at)
        if body.source_url:
            parsed = urlparse(body.source_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("source_url must be an absolute http or https URL.")
        ingested = datetime.now(timezone.utc)
        available = max(published, ingested)
        item = NewsEvent(symbol=symbol, headline=body.headline.strip(), source=body.source.strip(),
                         source_url=body.source_url.strip(), event_type=body.event_type.strip(),
                         published_at=published, ingested_at=ingested, available_at=available,
                         sentiment_score=score_headline(body.headline), relevance_score=body.relevance_score)
        db.add(item); db.commit(); db.refresh(item)
        return {"id": item.id, "symbol": item.symbol, "headline": item.headline, "source": item.source,
                "source_url": item.source_url, "event_type": item.event_type,
                "published_at": published.isoformat(), "ingested_at": ingested.isoformat(),
                "available_at": available.isoformat(), "sentiment_score": item.sentiment_score,
                "relevance_score": item.relevance_score,
                "timestamp_policy": "available_at=max(published_at, server_ingested_at); historical backfills cannot be used before ingestion"}
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=503, detail=f"News event could not be saved: {type(exc).__name__}.")


@app.get("/api/news/events")
def list_news_events(symbol: str | None = None, as_of: str | None = Query(None, max_length=64),
                     limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    """List news available by now or by a timezone-aware historical cutoff."""
    try:
        cutoff = parse_iso_datetime(as_of) if as_of else datetime.now(timezone.utc)
        query = db.query(NewsEvent).filter(NewsEvent.available_at <= cutoff)
        if symbol:
            query = query.filter(NewsEvent.symbol == symbol.strip().upper())
        rows = query.order_by(NewsEvent.available_at.desc()).limit(limit).all()
        def iso(value):
            return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).isoformat()
        return {"as_of": cutoff.isoformat(), "count": len(rows), "events": [
            {"id": r.id, "symbol": r.symbol, "headline": r.headline, "source": r.source,
             "source_url": r.source_url, "event_type": r.event_type,
             "published_at": iso(r.published_at), "ingested_at": iso(r.ingested_at),
             "available_at": iso(r.available_at), "sentiment_score": r.sentiment_score,
             "relevance_score": r.relevance_score} for r in rows],
            "policy": "Only events with available_at <= as_of are returned; missing historical availability is not inferred."}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/news/upstox/sync")
def sync_upstox_news(instrument_keys: str = Query(..., min_length=5, max_length=3200), db: Session = Depends(get_db)):
    """Fetch up to 30 instruments' recent Upstox headlines and persist timestamped evidence."""
    try:
        keys = list(dict.fromkeys(value.strip() for value in instrument_keys.split(",") if value.strip()))
        data = fetch_upstox_news(keys)
        now = datetime.now(timezone.utc)
        inserted = 0; duplicates = 0
        for article in data["articles"]:
            published = parse_iso_datetime(article["published_at"])
            key = article["instrument_key"]
            url = article["source_url"]
            exists = db.query(NewsEvent).filter(NewsEvent.symbol == key, NewsEvent.source_url == url,
                                                NewsEvent.headline == article["headline"]).first()
            if exists:
                duplicates += 1; continue
            db.add(NewsEvent(symbol=key, headline=article["headline"], source="Upstox News API",
                             source_url=url, event_type="news", published_at=published, ingested_at=now,
                             available_at=max(published, now), sentiment_score=article["sentiment_score"], relevance_score=1.0))
            inserted += 1
        db.commit()
        return {"provider":data["provider"], "fetched_at":data["fetched_at"], "requested_instruments":data["requested_instruments"],
                "articles_received":data["count"], "inserted":inserted, "duplicates_skipped":duplicates,
                "history_limit":data["history_limit"], "timestamp_policy":"available_at=max(published_at, server_ingested_at)"}
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        db.rollback(); raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=502, detail=f"Upstox news sync failed: {type(exc).__name__}. Check token and instrument keys.")


@app.get("/api/research/intraday/{symbol}")
def intraday_research(symbol: str, instrument_key: str = Query(..., min_length=5, max_length=100),
                      interval: int = Query(5, ge=1, le=300), folds: int = Query(3, ge=2, le=5),
                      cost_bps: float = Query(10.0, ge=0, le=100),
                      db: Session = Depends(get_db)):
    """Fetch real Upstox intraday candles and run chronological model comparisons."""
    try:
        normalized_interval = int(interval)
        if normalized_interval not in {1, 2, 3, 5, 10, 15, 30}:
            raise ValueError("Interval must be 1, 2, 3, 5, 10, 15 or 30 minutes.")
        data = fetch_upstox_historical(
            instrument_key=instrument_key,
            interval=normalized_interval,
        )

        import pandas as pd

        candle_frame = pd.DataFrame(data["candles"])
        engineered = build_intraday_features(candle_frame)
        # Load only news for the exact instrument key and align by available_at, never published_at alone.
        news_rows = (
            db.query(NewsEvent)
            .filter(
                NewsEvent.symbol == instrument_key,
                ~NewsEvent.source_url.like("https://example.com/article-test-%"),
            )
            .all()
        )
        news_payload = [{"available_at": row.available_at, "sentiment_score": row.sentiment_score,
                         "relevance_score": row.relevance_score} for row in news_rows]
        engineered = align_news_features(engineered, news_payload)
        evaluation = walk_forward_intraday(engineered, folds=folds, cost_bps=cost_bps)
        # V111 is a separate cost-aware three-class evaluation. Keep the existing
        # binary benchmark intact and expose V111 under its own response key.
        three_class_evaluation = walk_forward_three_class_intraday(
            engineered, folds=folds, cost_bps=cost_bps
        )
        evaluation["three_class_evaluation"] = three_class_evaluation
        return {"symbol": symbol.strip().upper(), "provider": data["provider"], "instrument_key": data["instrument_key"],
                "interval_minutes": normalized_interval, "fetched_at": data["fetched_at"],
                "candles_received": len(candle_frame), "latest_candle_at": str(candle_frame["timestamp"].iloc[-1]),
                "evaluation": evaluation, "news_feature_status": {"alignment_applied": True, "events_found": len(news_payload), "has_news_coverage": len(news_payload) > 0, "coverage_note": ("Matching news records were available for point-in-time alignment." if news_payload else "No stored news records matched this exact instrument key. News features remain neutral; historical news coverage is not established."), "features": ["news_event_count_24h", "news_sentiment_24h", "news_relevance_24h"], "alignment": "available_at <= candle timestamp; trailing 24 hours only"},
                "demo_trading_authorized": False, "disclaimer": "Research benchmark only. Binary and V111 three-class evaluations are historical diagnostics, not live order signals. No order is placed."}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Intraday research failed: {type(exc).__name__}. Check Upstox access and instrument key.")


@app.get("/api/research/status")
def research_status():
    """Describe implemented research inputs without claiming unavailable models are active."""
    import importlib.util
    return {"prediction_horizon": "intraday; target uses next three bars", "market_provider": "Upstox V3 intraday candles when configured",
            "news_events": "Upstox News API sync for up to 30 instrument keys plus timestamp-aware event storage; server ingestion time is enforced",
            "models": ["Random Forest baseline", "HistGradientBoosting", "Logistic Regression"],
            "news_features": ["news_event_count_24h", "news_sentiment_24h", "news_relevance_24h"],
            "lstm_gru": "optional chronological-fold benchmarks run only when PyTorch is installed and sufficient real data is available; otherwise reported as skipped",
            "pytorch_available": importlib.util.find_spec("torch") is not None,
            "demo_trading_gate": "always disabled by intraday research endpoint; calibrated probabilities and explicit evidence checks are reported, but no automatic order authorization is granted",
            "required_env": ["UPSTOX_ACCESS_TOKEN", "UPSTOX_INSTRUMENT_KEYS or a valid instrument_key query parameter"],
            "no_synthetic_market_data": True}



@app.get("/api/predict/{symbol}")
def prediction(
    symbol: str,
    include_walk_forward: bool = Query(
        False,
        description="Run five expanding-window chronological validation folds; slower but includes out-of-sample model comparison."
    ),
    db: Session = Depends(get_db),
):
    try:
        result = predict(symbol, include_walk_forward=include_walk_forward)

        # News is descriptive context; failure must not block price prediction.
        result["news_sentiment"] = fetch_live_news_sentiment(symbol)

    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Prediction could not be completed: {type(exc).__name__}. Check data availability and server logs."
        )

    # Save ordinary analysis history.
    history_saved = True
    try:
        db.add(
            AnalysisLog(
                symbol=result["symbol"],
                latest_close=result["latest_close"],
                signal=result["predicted_direction"],
                details=result["explanation"],
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        history_saved = False

    # Save one prospective prediction per symbol and market session.
    prospective_saved = False
    prospective_status = "not_recorded"

    direction = result.get("predicted_direction")
    prediction_date = result.get("latest_session_date")
    model_version = result.get("model_version")

    if (
        direction in ("UP", "DOWN")
        and prediction_date
        and model_version
        and result.get("latest_close") is not None
    ):
        try:
            existing = (
                db.query(ProspectivePrediction)
                .filter(
                    ProspectivePrediction.symbol == result["symbol"],
                    ProspectivePrediction.prediction_date == prediction_date,
                )
                .first()
            )

            if existing:
                prospective_saved = True
                prospective_status = "already_recorded"
            else:
                record = ProspectivePrediction(
                    symbol=result["symbol"],
                    prediction_date=prediction_date,
                    reference_close=float(result["latest_close"]),
                    predicted_class=1 if direction == "UP" else 0,
                    predicted_direction=direction,
                    up_probability=result.get("up_probability"),
                    model_version=model_version,
                    is_scored=False,
                )
                db.add(record)
                db.commit()

                prospective_saved = True
                prospective_status = "recorded"

        except Exception:
            db.rollback()
            prospective_saved = False
            prospective_status = "database_error"
    else:
        prospective_status = "prediction_not_eligible"

    return {
        **result,
        "history_saved": history_saved,
        "prospective_saved": prospective_saved,
        "prospective_status": prospective_status,
        "disclaimer": "Experimental analysis only; not investment advice."
    }


@app.post("/api/prospective-predictions/score")
def score_prospective_predictions(db: Session = Depends(get_db)):
    """
    Score pending predictions against the first later completed
    trading session. Never score against the prediction session
    or an unfinished current-day candle.
    """
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    import math
    import pandas as pd

    today_ist = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    pending = (
        db.query(ProspectivePrediction)
        .filter(ProspectivePrediction.is_scored.is_(False))
        .order_by(
            ProspectivePrediction.prediction_date.asc(),
            ProspectivePrediction.id.asc(),
        )
        .all()
    )

    history_cache = {}
    results = []

    for record in pending:
        symbol = record.symbol

        try:
            if symbol not in history_cache:
                history_cache[symbol] = fetch_daily_history(symbol, "5y")

            frame = history_cache[symbol]

            if frame is None or frame.empty:
                results.append({
                    "id": record.id,
                    "symbol": symbol,
                    "status": "no_market_data",
                })
                continue

            close_column = (
                "Close" if "Close" in frame.columns
                else "close" if "close" in frame.columns
                else None
            )

            if close_column is None:
                results.append({
                    "id": record.id,
                    "symbol": symbol,
                    "status": "missing_close_column",
                })
                continue

            prediction_date = datetime.strptime(
                record.prediction_date, "%Y-%m-%d"
            ).date()

            next_session = None

            for index, row in frame.sort_index().iterrows():
                session_timestamp = pd.Timestamp(index)

                if session_timestamp.tzinfo is not None:
                    session_date = (
                        session_timestamp
                        .tz_convert("Asia/Kolkata")
                        .date()
                    )
                else:
                    session_date = session_timestamp.date()

                # Must be strictly later than the prediction date
                # and must not be today's potentially incomplete candle.
                if session_date <= prediction_date or session_date >= today_ist:
                    continue

                actual_close = float(row[close_column])

                if not math.isfinite(actual_close) or actual_close <= 0:
                    continue

                next_session = (session_date, actual_close)
                break

            if next_session is None:
                results.append({
                    "id": record.id,
                    "symbol": symbol,
                    "prediction_date": record.prediction_date,
                    "status": "waiting_for_next_completed_session",
                })
                continue

            actual_date, actual_close = next_session

            # Binary target: 1 means the next close rose;
            # 0 means it did not rise.
            actual_class = int(actual_close > float(record.reference_close))
            actual_direction = "UP" if actual_class == 1 else "DOWN"

            record.actual_session_date = actual_date.isoformat()
            record.actual_close = actual_close
            record.actual_class = actual_class
            record.actual_direction = actual_direction
            record.is_correct = (
                int(record.predicted_class) == actual_class
            )
            record.is_scored = True
            record.scored_at = datetime.now(timezone.utc).replace(tzinfo=None)

            db.commit()

            results.append({
                "id": record.id,
                "symbol": symbol,
                "prediction_date": record.prediction_date,
                "actual_session_date": record.actual_session_date,
                "predicted_direction": record.predicted_direction,
                "actual_direction": actual_direction,
                "reference_close": float(record.reference_close),
                "actual_close": actual_close,
                "is_correct": record.is_correct,
                "status": "scored",
            })

        except Exception as exc:
            db.rollback()
            results.append({
                "id": record.id,
                "symbol": symbol,
                "status": "scoring_error",
                "error": type(exc).__name__,
            })

    return {
        "processed": len(results),
        "scored": sum(1 for item in results if item["status"] == "scored"),
        "pending": sum(
            1 for item in results
            if item["status"] == "waiting_for_next_completed_session"
        ),
        "results": results,
        "note": (
            "Only the first later completed daily session is used. "
            "This is prospective evaluation, not a guarantee of future performance."
        ),
    }


@app.get("/api/prospective-predictions/summary")
def prospective_predictions_summary(
    db: Session = Depends(get_db),
):
    """Summarize prospective results using persisted model fields."""
    import math

    records = (
        db.query(ProspectivePrediction)
        .order_by(
            ProspectivePrediction.prediction_date.asc(),
            ProspectivePrediction.id.asc(),
        )
        .all()
    )

    scored = [
        item for item in records
        if item.is_scored and item.actual_class is not None
    ]
    pending = [item for item in records if not item.is_scored]

    total_scored = len(scored)

    correct = sum(
        1 for item in scored
        if int(item.predicted_class) == int(item.actual_class)
    )

    incorrect = total_scored - correct

    accuracy = correct / total_scored if total_scored else None

    actual_up = [item for item in scored if int(item.actual_class) == 1]
    actual_down = [item for item in scored if int(item.actual_class) == 0]

    balanced_accuracy = None

    if actual_up and actual_down:
        up_recall = sum(
            1 for item in actual_up if int(item.predicted_class) == 1
        ) / len(actual_up)

        down_recall = sum(
            1 for item in actual_down if int(item.predicted_class) == 0
        ) / len(actual_down)

        balanced_accuracy = (up_recall + down_recall) / 2

    probability_rows = [
        item for item in scored
        if item.up_probability is not None
        and math.isfinite(float(item.up_probability))
        and 0 <= float(item.up_probability) <= 1
    ]

    brier_score = None

    if probability_rows:
        brier_score = sum(
            (
                float(item.up_probability)
                - int(item.actual_class)
            ) ** 2
            for item in probability_rows
        ) / len(probability_rows)

    return {
        "total_recorded": len(records),
        "total_scored": total_scored,
        "total_pending": len(pending),
        "correct_predictions": correct,
        "incorrect_predictions": incorrect,
        "accuracy": accuracy,
        "accuracy_percent": (
            round(accuracy * 100, 2)
            if accuracy is not None else None
        ),
        "balanced_accuracy": balanced_accuracy,
        "brier_score": brier_score,
        "brier_observations": len(probability_rows),
        "scoring_method": "first later completed daily trading session",
        "validation_note": (
            "Small samples are not reliable evidence of model quality. "
            "Probabilities are uncalibrated; Brier score is diagnostic only."
        ),
    }


@app.get("/api/history")
def history(limit: int = Query(30, ge=1, le=200), db: Session = Depends(get_db)):
    try:
        rows = db.query(AnalysisLog).order_by(AnalysisLog.created_at.desc()).limit(limit).all()
        return [{"id":r.id,"symbol":r.symbol,"latest_close":r.latest_close,"signal":r.signal,
                 "details":r.details,"created_at":r.created_at.isoformat()+"Z"} for r in rows]
    except Exception:
        db.rollback()
        raise HTTPException(status_code=503, detail="Analysis history is temporarily unavailable because the database cannot be reached.")

@app.get("/api/backtest/{symbol}/equity.csv")
def export_backtest_equity_csv(
    symbol: str,
    period: str = Query("1y", pattern="^(3mo|6mo|1y|2y|5y)$"),
    cost_bps: float = Query(10.0, ge=0, le=100, description="Estimated one-way transaction cost in basis points"),
):
    """Export daily strategy and buy-and-hold equity curves for reproducible inspection."""
    import csv
    import io
    import numpy as np
    import pandas as pd

    try:
        df = fetch_history(symbol, period).copy()
        if len(df) < 60:
            raise LookupError("At least 60 clean observations are required for this backtest.")
        close = pd.to_numeric(df["Close"], errors="coerce")
        sma20 = pd.to_numeric(df["SMA20"], errors="coerce")
        sma50 = pd.to_numeric(df["SMA50"], errors="coerce")
        valid = close.notna() & (close > 0)
        if int(valid.sum()) < 60:
            raise LookupError("At least 60 valid closing-price observations are required for this backtest.")
        close = close[valid]
        sma20 = sma20.reindex(close.index)
        sma50 = sma50.reindex(close.index)
        daily_returns = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
        position = (sma20 > sma50).shift(1).astype("boolean").fillna(False).astype(float)
        gross_returns = (daily_returns * position).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        changes = position.diff().abs()
        if len(changes):
            changes.iloc[0] = abs(float(position.iloc[0]))
        turnover = changes.fillna(0.0)
        costs = turnover * (cost_bps / 10000.0)
        net_returns = (gross_returns - costs).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        net_curve = (1.0 + net_returns).cumprod()
        gross_curve = (1.0 + gross_returns).cumprod()
        buy_hold_curve = (1.0 + daily_returns).cumprod()
        drawdown = net_curve / net_curve.cummax() - 1.0
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["date", "close", "position_long", "daily_market_return_pct", "daily_strategy_gross_return_pct", "estimated_cost_pct", "daily_strategy_net_return_pct", "strategy_gross_equity_base_1", "strategy_net_equity_base_1", "buy_hold_equity_base_1", "strategy_drawdown_pct"])
        dates = close.index
        for i, date in enumerate(dates):
            writer.writerow([
                str(date.date() if hasattr(date, "date") else date),
                round(float(close.iloc[i]), 6),
                int(position.iloc[i] > 0),
                round(float(daily_returns.iloc[i]) * 100, 6),
                round(float(gross_returns.iloc[i]) * 100, 6),
                round(float(costs.iloc[i]) * 100, 6),
                round(float(net_returns.iloc[i]) * 100, 6),
                round(float(gross_curve.iloc[i]), 8),
                round(float(net_curve.iloc[i]), 8),
                round(float(buy_hold_curve.iloc[i]), 8),
                round(float(drawdown.iloc[i]) * 100, 6),
            ])
        safe_symbol = "".join(ch for ch in symbol.upper() if ch.isalnum() or ch in "._-^")[:24] or "market"
        return Response(
            content=output.getvalue(), media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_symbol}-{period}-equity-curve.csv"',
                     "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Equity curve could not be exported: {type(exc).__name__}. Check market-data availability.")


@app.get("/api/backtest/{symbol}/export.csv")
def export_backtest_csv(
    symbol: str,
    period: str = Query("1y", pattern="^(3mo|6mo|1y|2y|5y)$"),
    cost_bps: float = Query(10.0, ge=0, le=100, description="Estimated one-way transaction cost in basis points"),
):
    """Export a backtest summary as CSV using the same calculation as the JSON endpoint."""
    import csv
    import io

    # Reuse the canonical calculation so CSV and dashboard figures cannot silently diverge.
    report = backtest(symbol=symbol, period=period, cost_bps=cost_bps)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    for key, value in report.items():
        if isinstance(value, list):
            value = " | ".join(str(item) for item in value)
        writer.writerow([key, value if value is not None else ""])
    safe_symbol = "".join(ch for ch in symbol.upper() if ch.isalnum() or ch in "._-^")[:24] or "market"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_symbol}-{period}-backtest.csv"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )

