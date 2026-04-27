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
    interval_seconds: int = 300
    state_path: str | None = None


# ── Response models ───────────────────────────────────────────────────────────

class FactorResponse(BaseModel):
    category: str
    name: str
    direction: str
    points: int
    detail: str = ""


class TimingResponse(BaseModel):
    action: str
    reason: str
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    time_horizon: str = "1w"


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
    timing: TimingResponse | None = None
    ohlcv: list[dict[str, Any]] = Field(default_factory=list)


class ScanResultResponse(BaseModel):
    ticker: str
    direction: str
    confidence: float
    top_factors: list[str] = Field(default_factory=list)
    factors: list[FactorResponse] = Field(default_factory=list)
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


class TradeResponse(BaseModel):
    ticker: str
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: str
    exit_time: str
    pnl: float
    return_pct: float
    reason: str
    is_win: bool


class EquityPointResponse(BaseModel):
    ts: str
    equity: float


class BacktestResponse(BaseModel):
    stats: BacktestStatsResponse
    trades: list[TradeResponse] = Field(default_factory=list)
    equity_curve: list[EquityPointResponse] = Field(default_factory=list)
    ohlcv: list[dict[str, Any]] = Field(default_factory=list)


class PositionResponse(BaseModel):
    ticker: str
    side: str
    quantity: int
    entry_price: float
    stop_loss: float
    take_profit: float


class RecentTradeResponse(BaseModel):
    ticker: str
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    exit_time: str
    reason: str


class TradingStatusResponse(BaseModel):
    running: bool
    tickers: list[str] = Field(default_factory=list)
    equity: float | None = None
    cash: float | None = None
    open_positions: int = 0
    positions: list[PositionResponse] = Field(default_factory=list)
    recent_trades: list[RecentTradeResponse] = Field(default_factory=list)
    cycle_count: int = 0


class PortfolioAnalyzeRequest(BaseModel):
    tickers: list[str]
    lookback_days: int = 252


class ETFInfoResponse(BaseModel):
    ticker: str
    name: str
    category: str
    tracked_index: str = ""
    expense_ratio: float | None = None
    is_etf: bool = True


class PortfolioAnalysisResponse(BaseModel):
    tickers: list[str]
    diversification_score: float
    correlation_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
    sector_exposure: dict[str, float] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    etf_infos: list[ETFInfoResponse] = Field(default_factory=list)
