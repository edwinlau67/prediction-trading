"""POST /predict/ — single-ticker prediction."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import FactorResponse, PredictRequest, PredictResponse, TimingResponse

router = APIRouter(prefix="/predict", tags=["prediction"])


@router.post("/", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    from prediction_trading.system import PredictionTradingSystem

    try:
        system = PredictionTradingSystem(
            ticker=req.ticker.upper(),
            enable_ai=req.enable_ai,
        )
        if req.categories:
            from prediction_trading.prediction import SignalScorer
            system.scorer = SignalScorer(categories=tuple(req.categories))

        market = system.fetch(lookback_days=req.lookback_days)
        prediction = system.predict(market)

        factors = [
            FactorResponse(
                category=str(f.category),
                name=f.name,
                direction=str(f.direction),
                points=f.points,
                detail=getattr(f, "detail", ""),
            )
            for f in (prediction.factors or [])
        ]

        timing = None
        if getattr(prediction, "timing", None) is not None:
            t = prediction.timing
            timing = TimingResponse(
                action=str(t.action),
                reason=t.reason,
                entry_price=getattr(t, "entry_price", None),
                stop_loss=getattr(t, "stop_loss", None),
                take_profit=getattr(t, "take_profit", None),
                time_horizon=getattr(t, "time_horizon", "1w"),
            )

        ohlcv: list[dict] = []
        if system._market and system._market.ohlcv is not None:
            for idx, row in system._market.ohlcv.tail(120).iterrows():
                ohlcv.append({
                    "date": str(idx.date()),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row.get("Volume", 0)),
                })

        return PredictResponse(
            ticker=prediction.ticker,
            direction=prediction.direction,
            confidence=prediction.confidence,
            current_price=prediction.current_price,
            price_target=getattr(prediction, "price_target", None),
            target_date=str(prediction.target_date) if getattr(prediction, "target_date", None) else None,
            risk_level=getattr(prediction, "risk_level", "medium"),
            factors=factors,
            meta=getattr(prediction, "meta", {}),
            timing=timing,
            ohlcv=ohlcv,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/macro")
def get_macro() -> dict:
    from prediction_trading.data_fetcher import DataFetcher
    try:
        ctx = DataFetcher().fetch_macro_context()
        indexes = []
        for idx in getattr(ctx, "indexes", []):
            indexes.append({
                "symbol": getattr(idx, "symbol", ""),
                "name": getattr(idx, "name", ""),
                "price": getattr(idx, "price", None),
                "change_1d_pct": getattr(idx, "change_1d_pct", None),
                "change_5d_pct": getattr(idx, "change_5d_pct", None),
                "change_30d_pct": getattr(idx, "change_30d_pct", None),
                "above_sma50": getattr(idx, "above_sma50", None),
            })
        return {
            "vix": getattr(ctx, "vix", None),
            "yield_10y": getattr(ctx, "yield_10y", None),
            "yield_2y": getattr(ctx, "yield_2y", None),
            "yield_spread": getattr(ctx, "yield_spread", None),
            "spy_above_sma50": getattr(ctx, "spy_above_sma50", None),
            "indexes": indexes,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
