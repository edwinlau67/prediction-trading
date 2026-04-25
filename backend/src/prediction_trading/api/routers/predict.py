"""POST /predict/ — single-ticker prediction."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import FactorResponse, PredictRequest, PredictResponse

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
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
