"""Pydantic v2 request/response schemas for the FastAPI layer."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Direction = Literal["bullish", "bearish", "neutral"]


# ── Request models ────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    ticker: str
    timeframe: str = "1w"
    enable_ai: bool = False
    lookback_days: int = 365
    categories: list[str] | None = None
    use_4h: bool = False


class ScanRequest(BaseModel):
    tickers: list[str]
    categories: list[str] | None = None
    min_confidence: float = 0.0
    workers: int = 4


class BacktestRequest(BaseModel):
    ticker: str
    start: str
    end: str
    initial_capital: float = 10_000.0
    commission: float = 1.0


class TradingStartRequest(BaseModel):
    tickers: list[str]
    initial_capital: float = 10_000.0
    dry_run: bool = True
    enforce_market_hours: bool = False


# ── Response models ───────────────────────────────────────────────────────────

class FactorResponse(BaseModel):
    category: str
    name: str
    direction: str
    points: int
    detail: str = ""


class PredictResponse(BaseModel):
    ticker: str
    direction: str
    confidence: float
    current_price: float
    price_target: float | None = None
    target_date: str | None = None
    risk_level: str = "medium"
    factors: list[FactorResponse] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class ScanResultResponse(BaseModel):
    ticker: str
    direction: str
    confidence: float
    top_factors: list[str] = Field(default_factory=list)
    current_price: float = 0.0
    error: str | None = None


class ScanResponse(BaseModel):
    results: list[ScanResultResponse]
    total: int


class BacktestStatsResponse(BaseModel):
    ticker: str = ""
    period: str = ""
    initial_capital: float = 0.0
    final_equity: float = 0.0
    return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    trades: int = 0
    win_rate_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float | None = None


class BacktestResponse(BaseModel):
    stats: BacktestStatsResponse


class TradingStatusResponse(BaseModel):
    running: bool
    tickers: list[str] = Field(default_factory=list)
    equity: float | None = None
    cash: float | None = None
    open_positions: int = 0
