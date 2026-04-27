"""POST /scan/ — multi-ticker watchlist scan."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import FactorResponse, ScanRequest, ScanResponse, ScanResultResponse

router = APIRouter(prefix="/scan", tags=["scanner"])


@router.post("/", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    from prediction_trading.scanner import WatchlistScanner

    try:
        scanner = WatchlistScanner(
            categories=tuple(req.categories) if req.categories else None,
            min_confidence=req.min_confidence,
            workers=req.workers,
        )
        results = scanner.scan([t.upper() for t in req.tickers])
        return ScanResponse(
            results=[
                ScanResultResponse(
                    ticker=r.ticker,
                    direction=r.direction,
                    confidence=r.confidence,
                    top_factors=r.top_factors or [],
                    factors=[
                        FactorResponse(
                            category=str(f.category),
                            name=f.name,
                            direction=str(f.direction),
                            points=f.points,
                            detail=f.detail,
                        )
                        for f in (r.factors or [])
                    ],
                    current_price=r.current_price or 0.0,
                    error=r.error,
                )
                for r in results
            ],
            total=len(results),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
