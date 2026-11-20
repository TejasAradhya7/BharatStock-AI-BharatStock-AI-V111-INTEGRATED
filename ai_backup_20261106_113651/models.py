from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class AnalysisLog(Base):
    __tablename__ = "analysis_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    latest_close: Mapped[float] = mapped_column(Float)
    signal: Mapped[str] = mapped_column(String(32))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TradeIdea(Base):
    """Persisted, research-only trade setup snapshots; these are not orders."""
    __tablename__ = "trade_ideas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    signal: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), default="watching", index=True)
    entry_price: Mapped[float] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class NewsEvent(Base):
    """Timestamped news/event evidence. available_at is the earliest time the app may use it."""
    __tablename__ = "news_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    headline: Mapped[str] = mapped_column(String(1000))
    source: Mapped[str] = mapped_column(String(120), default="user_supplied")
    source_url: Mapped[str] = mapped_column(String(2000), default="")
    event_type: Mapped[str] = mapped_column(String(80), default="news")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
