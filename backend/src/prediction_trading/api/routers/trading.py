"""GET /trading/status, POST /trading/start — AutoTrader control."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import (
    TradingStartRequest, TradingStatusResponse,
    PositionResponse, RecentTradeResponse,
)

router = APIRouter(prefix="/trading", tags=["trading"])

_active_trader = None


@router.get("/status", response_model=TradingStatusResponse)
def get_status() -> TradingStatusResponse:
    if _active_trader is None:
        return TradingStatusResponse(running=False)
    portfolio = getattr(_active_trader, "portfolio", None)

    positions: list[PositionResponse] = []
    if portfolio:
        for ticker, pos in getattr(portfolio, "positions", {}).items():
            positions.append(PositionResponse(
                ticker=ticker,
                side=str(pos.side),
                quantity=pos.quantity,
                entry_price=pos.entry_price,
                stop_loss=pos.stop_loss,
                take_profit=pos.take_profit,
            ))

    recent_trades: list[RecentTradeResponse] = []
    if portfolio:
        for t in list(reversed(getattr(portfolio, "closed_trades", [])))[:20]:
            recent_trades.append(RecentTradeResponse(
                ticker=t.ticker,
                side=str(t.side),
                quantity=t.quantity,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                pnl=t.pnl,
                return_pct=round(t.return_pct * 100, 2),
                exit_time=t.exit_time.isoformat() if t.exit_time else "",
                reason=t.reason,
            ))

    cycle_count = len(getattr(_active_trader, "_reports", []))

    return TradingStatusResponse(
        running=True,
        tickers=list(getattr(_active_trader, "tickers", [])),
        equity=portfolio.equity({}) if portfolio else None,
        cash=getattr(portfolio, "cash", None),
        open_positions=len(getattr(portfolio, "positions", {})),
        positions=positions,
        recent_trades=recent_trades,
        cycle_count=cycle_count,
    )


@router.post("/start", response_model=TradingStatusResponse)
def start_trading(req: TradingStartRequest) -> TradingStatusResponse:
    global _active_trader
    from prediction_trading.system import PredictionTradingSystem

    try:
        system = PredictionTradingSystem(
            ticker=req.tickers[0].upper(),
            initial_capital=req.initial_capital,
        )
        _active_trader = system.build_auto_trader(
            tickers=[t.upper() for t in req.tickers],
            dry_run=req.dry_run,
            enforce_market_hours=req.enforce_market_hours,
            state_path=req.state_path,
        )
        _active_trader._interval_seconds = req.interval_seconds
        return TradingStatusResponse(
            running=True,
            tickers=[t.upper() for t in req.tickers],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
