from pydantic import BaseModel, Field
from typing import Literal

class SentimentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)

class PredictionResponse(BaseModel):
    symbol: str
    latest_close: float
    predicted_direction: Literal["UP", "DOWN", "INSUFFICIENT_DATA"]
    model: str
    test_accuracy: float | None = None
    balanced_accuracy: float | None = None
    majority_baseline_accuracy: float | None = None
    test_observations: int | None = None
    up_probability: float | None = None
    explanation: str
    disclaimer: str = "Experimental analysis only; not investment advice."


class NewsEventRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    headline: str = Field(min_length=5, max_length=1000)
    published_at: str = Field(min_length=20, max_length=64)
    source: str = Field(default="user_supplied", min_length=1, max_length=120)
    source_url: str = Field(default="", max_length=2000)
    event_type: str = Field(default="news", min_length=1, max_length=80)
    relevance_score: float = Field(default=0.5, ge=0, le=1)
