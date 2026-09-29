"""The API "contract": what goes in and what comes out.
El "contrato" de la API: qué entra y qué sale."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Candle(BaseModel):
    time: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)


class CandlesRequest(BaseModel):
    """Send the latest closed H1 candles (≥ 250) — the API builds the clues itself."""
    candles: list[Candle] = Field(min_length=250)


class FeaturesRequest(BaseModel):
    """Already-computed clues (advanced use)."""
    features: dict[str, float]


class Prediction(BaseModel):
    direction: Literal["UP", "DOWN"]
    prob_up: float
    based_on_candle: datetime | None = None
    model: str
    model_version: int | None = None


class HistoryPoint(BaseModel):
    time: datetime
    close: float
    prob_up: float


class History(BaseModel):
    """Probability of UP for every candle where the clues can be computed (for charts)."""
    model: str
    points: list[HistoryPoint]


class ModelInfo(BaseModel):
    model: str
    version: int | None
    registered_model: str | None
    trained_test_period: list[str]
    metrics: dict[str, float]
    features: list[str]
