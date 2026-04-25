"""GET /trading/status, POST /trading/start — AutoTrader control."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import TradingStartRequest, TradingStatusResponse

router = APIRouter(prefix="/trading", tags=["trading"])

_active_trader = None


@router.get("/status", response_model=TradingStatusResponse)
def get_status() -> TradingStatusResponse:
    if _active_trader is None:
        return TradingStatusResponse(running=False)
    portfolio = getattr(_active_trader, "portfolio", None)
    return TradingStatusResponse(
        running=True,
        tickers=list(getattr(_active_trader, "tickers", [])),
        equity=portfolio.equity({}) if portfolio else None,
        cash=getattr(portfolio, "cash", None),
        open_positions=len(getattr(portfolio, "positions", {})),
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
        )
        return TradingStatusResponse(
            running=True,
            tickers=[t.upper() for t in req.tickers],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
