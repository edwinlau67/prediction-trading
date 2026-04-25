"""POST /backtest/ — historical bar-by-bar backtest."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import BacktestRequest, BacktestResponse, BacktestStatsResponse

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/", response_model=BacktestResponse)
def run_backtest(req: BacktestRequest) -> BacktestResponse:
    from prediction_trading.system import PredictionTradingSystem

    try:
        system = PredictionTradingSystem(
            ticker=req.ticker.upper(),
            initial_capital=req.initial_capital,
        )
        system.cfg.portfolio["commission_per_trade"] = req.commission
        result = system.backtest(req.start, req.end)
        raw = result.summary()
        stats = BacktestStatsResponse(
            ticker=req.ticker.upper(),
            period=f"{req.start} – {req.end}",
            initial_capital=req.initial_capital,
            final_equity=raw.get("final_equity", 0.0),
            return_pct=raw.get("return_pct", 0.0),
            max_drawdown_pct=raw.get("max_drawdown_pct", 0.0),
            trades=raw.get("trades", 0),
            win_rate_pct=raw.get("win_rate_pct", 0.0),
            avg_win=raw.get("avg_win", 0.0),
            avg_loss=raw.get("avg_loss", 0.0),
            profit_factor=raw.get("profit_factor"),
        )
        return BacktestResponse(stats=stats)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
