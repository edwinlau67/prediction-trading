"""Rule-based watchlist scanner.

Runs SignalScorer over a list of tickers in parallel and returns results
ranked by confidence. No AI, no charting — designed for quick screening.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from .data_fetcher import DataFetcher
from .indicators import TechnicalIndicators
from .prediction.factor import ALL_CATEGORIES
from .prediction.signal_scorer import SignalScorer


@dataclass
class ScanResult:
    ticker: str
    direction: str          # "bullish" | "bearish" | "neutral"
    confidence: float
    top_factors: list[str] = field(default_factory=list)
    current_price: float = 0.0
    error: str | None = None


class WatchlistScanner:
    """Screen multiple tickers with the rule-based engine."""

    def __init__(
        self,
        *,
        categories: tuple[str, ...] | None = None,
        lookback_days: int = 365,
        min_confidence: float = 0.0,
        workers: int = 4,
    ) -> None:
        self.categories = tuple(categories) if categories else ALL_CATEGORIES
        self.lookback_days = lookback_days
        self.min_confidence = min_confidence
        self.workers = max(1, workers)
        self._fetcher = DataFetcher()
        self._scorer = SignalScorer(categories=self.categories)

    def scan(self, tickers: list[str]) -> list[ScanResult]:
        """Return results ranked by confidence descending."""
        results: list[ScanResult] = []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self._scan_one, t.upper()): t for t in tickers}
            for fut in as_completed(futures):
                results.append(fut.result())

        results.sort(key=lambda r: (r.error is not None, -r.confidence))
        if self.min_confidence > 0:
            results = [r for r in results
                       if r.error is not None or r.confidence >= self.min_confidence]
        return results

    def _scan_one(self, ticker: str) -> ScanResult:
        try:
            market = self._fetcher.fetch(ticker, lookback_days=self.lookback_days,
                                         include_fundamentals=False)
            df = TechnicalIndicators.compute_all(market.ohlcv)
            score = self._scorer.score(df)
            top = sorted(score.factors, key=lambda f: abs(f.signed), reverse=True)[:3]
            return ScanResult(
                ticker=ticker,
                direction=score.direction,
                confidence=round(score.confidence, 3),
                top_factors=[f.label for f in top],
                current_price=round(market.current_price, 4),
            )
        except Exception as exc:
            return ScanResult(
                ticker=ticker,
                direction="neutral",
                confidence=0.0,
                error=str(exc),
            )
