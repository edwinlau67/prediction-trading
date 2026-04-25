"""Data fetcher backed by Yahoo Finance (yfinance).

Returns a uniform OHLCV DataFrame plus a fundamentals dict so downstream
indicators and the AI predictor can consume a single source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - import-time guard only
    yf = None  # type: ignore[assignment]


@dataclass
class MarketData:
    """Container for OHLCV history plus latest price and fundamentals."""

    ticker: str
    ohlcv: pd.DataFrame
    current_price: float
    fundamentals: dict[str, Any] = field(default_factory=dict)
    interval: str = "1d"

    @property
    def as_of(self) -> pd.Timestamp:
        return self.ohlcv.index[-1]


class DataFetcher:
    """Thin wrapper around yfinance with graceful fallbacks."""

    def __init__(self, *, interval: str = "1d") -> None:
        if yf is None:
            raise ImportError(
                "yfinance is not installed. Run `pip install -r requirements.txt`."
            )
        self.interval = interval

    def fetch_history(
        self,
        ticker: str,
        *,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        lookback_days: int | None = None,
    ) -> pd.DataFrame:
        """Download OHLCV history. Supply either (start, end) or lookback_days."""
        if start is None and lookback_days is not None:
            start_dt = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            start = start_dt.strftime("%Y-%m-%d")
        if end is None:
            end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        df = yf.download(
            ticker,
            start=start,
            end=end,
            interval=self.interval,
            progress=False,
            auto_adjust=False,
            group_by="column",
        )
        if df is None or df.empty:
            raise ValueError(f"No price history returned for {ticker!r}.")

        # yfinance sometimes returns a MultiIndex even for a single ticker.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        df.index = pd.to_datetime(df.index)
        # Drop bars where OHLC constraints are violated (data quality guard)
        valid = (
            (df["High"] >= df["Open"]) & (df["High"] >= df["Close"]) &
            (df["Low"] <= df["Open"]) & (df["Low"] <= df["Close"]) &
            (df["High"] >= df["Low"])
        )
        n_bad = (~valid).sum()
        if n_bad > 0:
            import logging
            logging.getLogger("prediction_trading.data_fetcher").warning(
                "Dropped %d bar(s) with invalid OHLC for %s", n_bad, ticker
            )
            df = df[valid]
        return df

    def fetch_fundamentals(self, ticker: str) -> dict[str, Any]:
        """Best-effort fundamentals snapshot. Missing values stay absent."""
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            info = {}
        keys = (
            "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
            "enterpriseToEbitda", "pegRatio", "revenueGrowth", "earningsGrowth",
            "profitMargins", "operatingMargins", "returnOnEquity", "debtToEquity",
            "currentRatio", "dividendYield", "shortRatio", "marketCap",
        )
        return {k: info.get(k) for k in keys if info.get(k) is not None}

    def fetch(
        self,
        ticker: str,
        *,
        lookback_days: int = 365,
        include_fundamentals: bool = True,
    ) -> MarketData:
        ticker = ticker.upper().strip()
        ohlcv = self.fetch_history(ticker, lookback_days=lookback_days)
        current = float(ohlcv["Close"].iloc[-1])
        fund = self.fetch_fundamentals(ticker) if include_fundamentals else {}
        return MarketData(
            ticker=ticker,
            ohlcv=ohlcv,
            current_price=current,
            fundamentals=fund,
            interval=self.interval,
        )
