"""POST /portfolio/analyze — ETF/stock correlation and diversification analysis."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import (
    ETFInfoResponse, PortfolioAnalyzeRequest, PortfolioAnalysisResponse,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/analyze", response_model=PortfolioAnalysisResponse)
def analyze_portfolio(req: PortfolioAnalyzeRequest) -> PortfolioAnalysisResponse:
    from prediction_trading.etf import ETFAnalyzer

    try:
        result = ETFAnalyzer().analyze_portfolio(
            [t.upper() for t in req.tickers],
            lookback_days=req.lookback_days,
        )

        corr_dict: dict[str, dict[str, float]] = {}
        if not result.correlation_matrix.empty:
            corr_dict = {
                col: {row: round(float(val), 4) for row, val in result.correlation_matrix[col].items()}
                for col in result.correlation_matrix.columns
            }

        etf_infos = [
            ETFInfoResponse(
                ticker=info.ticker,
                name=info.name,
                category=info.category,
                tracked_index=info.tracked_index,
                expense_ratio=info.expense_ratio,
                is_etf=info.is_etf,
            )
            for info in result.etf_infos
        ]

        return PortfolioAnalysisResponse(
            tickers=[t.upper() for t in req.tickers],
            diversification_score=round(result.diversification_score, 4),
            correlation_matrix=corr_dict,
            sector_exposure=result.sector_exposure,
            recommendations=result.recommendations,
            etf_infos=etf_infos,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
