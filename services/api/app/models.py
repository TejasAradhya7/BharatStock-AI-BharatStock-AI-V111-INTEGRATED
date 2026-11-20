from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
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


class PredictionEvaluation(Base):
    """Prospective next-session prediction evaluation records."""
    __tablename__ = "prediction_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    model_name: Mapped[str] = mapped_column(String(100))
    prediction_time: Mapped[datetime] = mapped_column(DateTime, index=True)

    reference_close: Mapped[float] = mapped_column(Float)
    predicted_direction: Mapped[str] = mapped_column(String(16))
    up_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Populated only after the next valid trading session is observed.
    outcome_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ProspectivePrediction(Base):
    """Predictions recorded before their next-session outcomes are known."""

    __tablename__ = "prospective_predictions"

    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "prediction_date",
            name="uq_prospective_symbol_prediction_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    prediction_date: Mapped[str] = mapped_column(String(10), index=True)

    reference_close: Mapped[float] = mapped_column(Float)
    predicted_class: Mapped[int] = mapped_column(Integer)
    predicted_direction: Mapped[str] = mapped_column(String(8))
    up_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(100))

    actual_session_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    actual_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_class: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_scored: Mapped[bool] = mapped_column(default=False)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
