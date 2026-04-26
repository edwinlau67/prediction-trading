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


_BULLISH_WORDS = frozenset({
    "beat", "surges", "surge", "upgrade", "raises", "record",
    "buyback", "outperform", "growth", "rally",
})
_BEARISH_WORDS = frozenset({
    "miss", "falls", "fall", "downgrade", "cuts", "layoff",
    "recall", "lawsuit", "fraud", "warning", "decline",
})

_SECTOR_ETF_MAP: dict[str, str] = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Financials": "XLF",
    "Energy": "XLE",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}


@dataclass
class NewsContext:
    """News sentiment + earnings data for a single ticker."""

    sentiment_score: float           # -1.0 .. 1.0 keyword ratio
    article_count: int
    recent_headlines: list[str]      # up to 5
    earnings_beat: bool | None       # None = no recent data
    earnings_miss: bool | None
    earnings_upcoming_days: int | None  # None = not within 30d


@dataclass
class IndexSnapshot:
    """Price snapshot for a single market index."""

    symbol: str
    name: str
    price: float | None
    change_1d_pct: float | None
    change_5d_pct: float | None
    change_30d_pct: float | None
    above_sma50: bool | None
    above_sma200: bool | None
    ohlcv_30d: pd.DataFrame | None = field(default=None, repr=False, compare=False)

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change_1d_pct": self.change_1d_pct,
            "change_5d_pct": self.change_5d_pct,
            "change_30d_pct": self.change_30d_pct,
            "above_sma50": self.above_sma50,
            "above_sma200": self.above_sma200,
        }


@dataclass
class MacroContext:
    """Macro economic snapshot fetched from yfinance index symbols."""

    vix: float | None
    yield_10y: float | None
    yield_2y: float | None
    yield_spread: float | None       # 10Y - 2Y
    spy_above_sma50: bool | None
    indexes: list[IndexSnapshot] = field(default_factory=list)


@dataclass
class SectorContext:
    """Sector relative-strength context for a single ticker."""

    sector: str
    sector_etf: str                  # e.g. "XLK"
    stock_30d_return: float | None
    sector_30d_return: float | None
    spy_30d_return: float | None
    vs_sector: float | None          # stock_30d - sector_30d
    sector_vs_spy: float | None      # sector_30d - spy_30d


@dataclass
class MarketData:
    """Container for OHLCV history plus latest price and fundamentals."""

    ticker: str
    ohlcv: pd.DataFrame
    current_price: float
    fundamentals: dict[str, Any] = field(default_factory=dict)
    interval: str = "1d"
    news_context: NewsContext | None = None
    macro_context: MacroContext | None = None
    sector_context: SectorContext | None = None

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

    def fetch_news_context(self, ticker: str) -> NewsContext:
        """Keyword-based news sentiment + earnings calendar from yfinance."""
        try:
            t = yf.Ticker(ticker)
            news = t.news or []
        except Exception:
            news = []

        bullish_count = bearish_count = 0
        headlines: list[str] = []
        for item in news[:20]:
            title = (item.get("title") or "").lower()
            headlines.append(item.get("title", ""))
            if any(w in title for w in _BULLISH_WORDS):
                bullish_count += 1
            if any(w in title for w in _BEARISH_WORDS):
                bearish_count += 1

        total = bullish_count + bearish_count
        sentiment = (bullish_count - bearish_count) / total if total else 0.0

        earnings_beat: bool | None = None
        earnings_miss: bool | None = None
        try:
            t = yf.Ticker(ticker)
            ed = t.earnings_dates
            if ed is not None and not ed.empty:
                col_est = "EPS Estimate"
                col_act = "Reported EPS"
                if col_est in ed.columns and col_act in ed.columns:
                    recent = ed.dropna(subset=[col_est, col_act]).head(1)
                    if not recent.empty:
                        est = float(recent[col_est].iloc[0])
                        actual = float(recent[col_act].iloc[0])
                        if actual > est:
                            earnings_beat = True
                        elif actual < est:
                            earnings_miss = True
        except Exception:
            pass

        earnings_upcoming_days: int | None = None
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if cal is not None:
                next_date: pd.Timestamp | None = None
                if isinstance(cal, pd.DataFrame) and "Earnings Date" in cal.index:
                    next_date = pd.Timestamp(cal.loc["Earnings Date"].iloc[0])
                elif isinstance(cal, dict) and "Earnings Date" in cal:
                    dates = cal["Earnings Date"]
                    if dates:
                        next_date = pd.Timestamp(dates[0])
                if next_date is not None:
                    now = pd.Timestamp.now(tz=next_date.tzinfo)
                    delta = (next_date - now).days
                    if 0 <= delta <= 30:
                        earnings_upcoming_days = delta
        except Exception:
            pass

        return NewsContext(
            sentiment_score=round(sentiment, 3),
            article_count=len(news),
            recent_headlines=headlines[:5],
            earnings_beat=earnings_beat,
            earnings_miss=earnings_miss,
            earnings_upcoming_days=earnings_upcoming_days,
        )

    @staticmethod
    def _fetch_index_snapshot(sym: str, name: str) -> IndexSnapshot:
        """Fetch price, change %, and trend for a single market index symbol."""
        try:
            df = yf.download(sym, period="3mo", progress=False, auto_adjust=True)
            if df is None or df.empty:
                return IndexSnapshot(symbol=sym, name=name, price=None,
                                     change_1d_pct=None, change_5d_pct=None,
                                     change_30d_pct=None, above_sma50=None,
                                     above_sma200=None)
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            close = close.dropna()
            if close.empty:
                return IndexSnapshot(symbol=sym, name=name, price=None,
                                     change_1d_pct=None, change_5d_pct=None,
                                     change_30d_pct=None, above_sma50=None,
                                     above_sma200=None)

            price = float(close.iloc[-1])

            def _pct(n: int) -> float | None:
                if len(close) > n:
                    return float((close.iloc[-1] / close.iloc[-1 - n] - 1) * 100)
                return None

            change_1d = _pct(1)
            change_5d = _pct(5)
            change_30d = _pct(30)

            sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
            sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

            return IndexSnapshot(
                symbol=sym, name=name, price=price,
                change_1d_pct=change_1d, change_5d_pct=change_5d, change_30d_pct=change_30d,
                above_sma50=price > sma50 if sma50 is not None else None,
                above_sma200=price > sma200 if sma200 is not None else None,
                ohlcv_30d=df.tail(30),
            )
        except Exception:
            return IndexSnapshot(symbol=sym, name=name, price=None,
                                 change_1d_pct=None, change_5d_pct=None,
                                 change_30d_pct=None, above_sma50=None,
                                 above_sma200=None)

    def fetch_macro_context(self) -> MacroContext:
        """VIX, yield curve, SPY trend, and major index snapshots from yfinance."""

        def _last_close(sym: str, period: str = "5d") -> float | None:
            try:
                df = yf.download(sym, period=period, progress=False, auto_adjust=True)
                if df is None or df.empty:
                    return None
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                vals = close.dropna()
                return float(vals.iloc[-1]) if not vals.empty else None
            except Exception:
                return None

        vix = _last_close("^VIX", "5d")
        y10 = _last_close("^TNX", "5d")
        y2 = _last_close("^IRX", "5d")
        spread = (y10 - y2) if (y10 is not None and y2 is not None) else None

        spy_above_sma50: bool | None = None
        try:
            spy_df = yf.download("SPY", period="3mo", progress=False, auto_adjust=True)
            if spy_df is not None and not spy_df.empty:
                close = spy_df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if len(close) >= 50:
                    sma50 = float(close.rolling(50).mean().iloc[-1])
                    spy_above_sma50 = float(close.iloc[-1]) > sma50
        except Exception:
            pass

        _INDEX_MAP = [("^DJI", "DOW"), ("^IXIC", "NASDAQ"), ("^GSPC", "S&P 500")]
        indexes = [self._fetch_index_snapshot(sym, name) for sym, name in _INDEX_MAP]

        return MacroContext(
            vix=vix,
            yield_10y=y10,
            yield_2y=y2,
            yield_spread=spread,
            spy_above_sma50=spy_above_sma50,
            indexes=indexes,
        )

    def fetch_sector_context(self, ticker: str, stock_ohlcv: pd.DataFrame) -> SectorContext:
        """Sector ETF relative strength vs SPY over the last 30 days."""
        sector = "Unknown"
        sector_etf = "SPY"
        try:
            info = yf.Ticker(ticker).info or {}
            sector = info.get("sector", "Unknown") or "Unknown"
            sector_etf = _SECTOR_ETF_MAP.get(sector, "SPY")
        except Exception:
            pass

        def _30d_return(df: pd.DataFrame) -> float | None:
            if df is None or df.empty:
                return None
            try:
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if len(close) < 2:
                    return None
                return float((close.iloc[-1] / close.iloc[0]) - 1.0)
            except Exception:
                return None

        stock_30d = _30d_return(stock_ohlcv.tail(30)) if not stock_ohlcv.empty else None

        sector_30d: float | None = None
        spy_30d: float | None = None
        try:
            sec_df = yf.download(sector_etf, period="1mo", progress=False, auto_adjust=True)
            sector_30d = _30d_return(sec_df)
            spy_df = yf.download("SPY", period="1mo", progress=False, auto_adjust=True)
            spy_30d = _30d_return(spy_df)
        except Exception:
            pass

        vs_sector = (
            stock_30d - sector_30d
            if stock_30d is not None and sector_30d is not None
            else None
        )
        sector_vs_spy = (
            sector_30d - spy_30d
            if sector_30d is not None and spy_30d is not None
            else None
        )

        return SectorContext(
            sector=sector,
            sector_etf=sector_etf,
            stock_30d_return=stock_30d,
            sector_30d_return=sector_30d,
            spy_30d_return=spy_30d,
            vs_sector=vs_sector,
            sector_vs_spy=sector_vs_spy,
        )

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
        include_enriched: bool = False,
    ) -> MarketData:
        ticker = ticker.upper().strip()
        ohlcv = self.fetch_history(ticker, lookback_days=lookback_days)
        current = float(ohlcv["Close"].iloc[-1])
        fund = self.fetch_fundamentals(ticker) if include_fundamentals else {}

        news_ctx: NewsContext | None = None
        macro_ctx: MacroContext | None = None
        sector_ctx: SectorContext | None = None
        if include_enriched:
            try:
                news_ctx = self.fetch_news_context(ticker)
            except Exception:
                pass
            try:
                macro_ctx = self.fetch_macro_context()
            except Exception:
                pass
            try:
                sector_ctx = self.fetch_sector_context(ticker, ohlcv)
            except Exception:
                pass

        return MarketData(
            ticker=ticker,
            ohlcv=ohlcv,
            current_price=current,
            fundamentals=fund,
            interval=self.interval,
            news_context=news_ctx,
            macro_context=macro_ctx,
            sector_context=sector_ctx,
        )
