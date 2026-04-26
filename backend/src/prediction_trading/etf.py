"""ETF metadata and portfolio combination analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]


# Built-in catalogue for major ETFs — avoids a network round-trip for common lookups.
_ETF_CATALOGUE: dict[str, dict[str, Any]] = {
    # Broad market
    "SPY":  {"name": "SPDR S&P 500 ETF",           "category": "US Large Blend",    "tracked_index": "S&P 500",       "expense_ratio": 0.0945},
    "IVV":  {"name": "iShares Core S&P 500",        "category": "US Large Blend",    "tracked_index": "S&P 500",       "expense_ratio": 0.03},
    "VOO":  {"name": "Vanguard S&P 500 ETF",        "category": "US Large Blend",    "tracked_index": "S&P 500",       "expense_ratio": 0.03},
    "QQQ":  {"name": "Invesco QQQ ETF",             "category": "US Large Growth",   "tracked_index": "NASDAQ-100",    "expense_ratio": 0.20},
    "IWM":  {"name": "iShares Russell 2000",        "category": "US Small Blend",    "tracked_index": "Russell 2000",  "expense_ratio": 0.19},
    "VTI":  {"name": "Vanguard Total Stock Market", "category": "US Total Market",   "tracked_index": "CRSP US Total", "expense_ratio": 0.03},
    "DIA":  {"name": "SPDR Dow Jones Industrial",   "category": "US Large Value",    "tracked_index": "DJIA",          "expense_ratio": 0.16},
    # Sector ETFs (SPDR)
    "XLK":  {"name": "SPDR Technology Sector",      "category": "Sector — Technology",    "tracked_index": "S&P Tech",       "expense_ratio": 0.10},
    "XLV":  {"name": "SPDR Health Care Sector",     "category": "Sector — Healthcare",    "tracked_index": "S&P Health",     "expense_ratio": 0.10},
    "XLF":  {"name": "SPDR Financial Sector",       "category": "Sector — Financials",    "tracked_index": "S&P Financials", "expense_ratio": 0.10},
    "XLE":  {"name": "SPDR Energy Sector",          "category": "Sector — Energy",        "tracked_index": "S&P Energy",     "expense_ratio": 0.10},
    "XLY":  {"name": "SPDR Consumer Discret.",      "category": "Sector — Consumer Cycl.","tracked_index": "S&P Cons.Disc.", "expense_ratio": 0.10},
    "XLP":  {"name": "SPDR Consumer Staples",       "category": "Sector — Consumer Def.", "tracked_index": "S&P Cons.Stap.", "expense_ratio": 0.10},
    "XLI":  {"name": "SPDR Industrial Sector",      "category": "Sector — Industrials",   "tracked_index": "S&P Industrial", "expense_ratio": 0.10},
    "XLB":  {"name": "SPDR Materials Sector",       "category": "Sector — Materials",     "tracked_index": "S&P Materials",  "expense_ratio": 0.10},
    "XLRE": {"name": "SPDR Real Estate Sector",     "category": "Sector — Real Estate",   "tracked_index": "S&P Real Estate","expense_ratio": 0.10},
    "XLU":  {"name": "SPDR Utilities Sector",       "category": "Sector — Utilities",     "tracked_index": "S&P Utilities",  "expense_ratio": 0.10},
    "XLC":  {"name": "SPDR Comm. Services Sector",  "category": "Sector — Comm. Svcs",    "tracked_index": "S&P Comm.Svcs",  "expense_ratio": 0.10},
    # Bonds & alternatives
    "BND":  {"name": "Vanguard Total Bond Market",  "category": "Intermediate-Term Bond", "tracked_index": "Bloomberg US Agg","expense_ratio": 0.03},
    "AGG":  {"name": "iShares Core US Agg Bond",    "category": "Intermediate-Term Bond", "tracked_index": "Bloomberg US Agg","expense_ratio": 0.03},
    "TLT":  {"name": "iShares 20+ Year Tsy Bond",   "category": "Long-Term Bond",         "tracked_index": "ICE 20+ Tsy",    "expense_ratio": 0.15},
    "GLD":  {"name": "SPDR Gold Shares",            "category": "Commodities — Gold",     "tracked_index": "Gold Spot",      "expense_ratio": 0.40},
    "IAU":  {"name": "iShares Gold Trust",          "category": "Commodities — Gold",     "tracked_index": "Gold Spot",      "expense_ratio": 0.25},
    "SLV":  {"name": "iShares Silver Trust",        "category": "Commodities — Silver",   "tracked_index": "Silver Spot",    "expense_ratio": 0.50},
    # International
    "VEA":  {"name": "Vanguard FTSE Dev. Markets",  "category": "Foreign Large Blend",    "tracked_index": "FTSE Dev.",      "expense_ratio": 0.05},
    "VWO":  {"name": "Vanguard FTSE Emg. Markets",  "category": "Diversified Emg. Mkts",  "tracked_index": "FTSE EM",        "expense_ratio": 0.08},
    "EFA":  {"name": "iShares MSCI EAFE",           "category": "Foreign Large Blend",    "tracked_index": "MSCI EAFE",      "expense_ratio": 0.32},
}

# Broad sector for each ETF category (used for exposure reporting)
_CATEGORY_SECTOR: dict[str, str] = {
    "US Large Blend": "US Equity",
    "US Large Growth": "US Equity",
    "US Large Value": "US Equity",
    "US Small Blend": "US Equity",
    "US Total Market": "US Equity",
    "Sector — Technology": "Technology",
    "Sector — Healthcare": "Healthcare",
    "Sector — Financials": "Financials",
    "Sector — Energy": "Energy",
    "Sector — Consumer Cycl.": "Consumer",
    "Sector — Consumer Def.": "Consumer",
    "Sector — Industrials": "Industrials",
    "Sector — Materials": "Materials",
    "Sector — Real Estate": "Real Estate",
    "Sector — Utilities": "Utilities",
    "Sector — Comm. Svcs": "Communication",
    "Intermediate-Term Bond": "Fixed Income",
    "Long-Term Bond": "Fixed Income",
    "Commodities — Gold": "Commodities",
    "Commodities — Silver": "Commodities",
    "Foreign Large Blend": "International",
    "Diversified Emg. Mkts": "International",
}


@dataclass
class ETFInfo:
    ticker: str
    name: str
    category: str
    tracked_index: str
    expense_ratio: float | None
    is_etf: bool


@dataclass
class PortfolioAnalysis:
    tickers: list[str]
    correlation_matrix: pd.DataFrame
    diversification_score: float          # 0–1; lower avg correlation = higher score
    sector_exposure: dict[str, float]     # sector → equal-weight fraction
    recommendations: list[str]
    etf_infos: list[ETFInfo] = field(default_factory=list)


class ETFAnalyzer:
    """ETF metadata lookup and portfolio-level combination analysis."""

    def get_etf_info(self, ticker: str) -> ETFInfo:
        t = ticker.upper()
        catalogue = _ETF_CATALOGUE.get(t)
        if catalogue:
            return ETFInfo(
                ticker=t,
                name=catalogue["name"],
                category=catalogue["category"],
                tracked_index=catalogue["tracked_index"],
                expense_ratio=catalogue.get("expense_ratio"),
                is_etf=True,
            )
        # Try yfinance for unlisted tickers
        try:
            if yf is None:
                raise ImportError("yfinance not available")
            info = yf.Ticker(t).info or {}
            quote_type = info.get("quoteType", "").upper()
            return ETFInfo(
                ticker=t,
                name=info.get("longName") or info.get("shortName") or t,
                category=info.get("category") or info.get("fundFamily") or "Unknown",
                tracked_index=info.get("legalType") or "Unknown",
                expense_ratio=info.get("annualReportExpenseRatio") or info.get("totalExpenseRatio"),
                is_etf=quote_type in ("ETF", "ETP"),
            )
        except Exception:
            return ETFInfo(
                ticker=t, name=t, category="Unknown",
                tracked_index="Unknown", expense_ratio=None, is_etf=False,
            )

    def is_etf(self, ticker: str) -> bool:
        return self.get_etf_info(ticker).is_etf

    def analyze_portfolio(
        self,
        tickers: list[str],
        lookback_days: int = 252,
    ) -> PortfolioAnalysis:
        tickers = [t.upper() for t in tickers]
        etf_infos = [self.get_etf_info(t) for t in tickers]

        # Fetch close prices
        prices = self._fetch_closes(tickers, lookback_days)
        valid = [t for t in tickers if t in prices.columns and not prices[t].dropna().empty]

        if len(valid) < 2:
            corr = pd.DataFrame(index=valid, columns=valid, data=1.0) if valid else pd.DataFrame()
            return PortfolioAnalysis(
                tickers=tickers,
                correlation_matrix=corr,
                diversification_score=1.0,
                sector_exposure={},
                recommendations=["Need at least 2 tickers with price history for correlation analysis."],
                etf_infos=etf_infos,
            )

        returns = prices[valid].pct_change().dropna()
        corr = returns.corr()

        # Diversification score: 1 - mean(|off-diagonal correlations|)
        n = len(valid)
        if n > 1:
            mask = ~pd.DataFrame(
                [[i == j for j in range(n)] for i in range(n)],
                index=valid, columns=valid,
                dtype=bool,
            )
            off_diag = corr.where(mask).stack()
            div_score = float(1.0 - off_diag.abs().mean())
        else:
            div_score = 1.0

        # Sector exposure (equal-weighted)
        sector_exposure: dict[str, float] = {}
        for info in etf_infos:
            if info.ticker in valid:
                sector = _CATEGORY_SECTOR.get(info.category, info.category)
                sector_exposure[sector] = sector_exposure.get(sector, 0.0) + 1.0 / len(valid)

        recommendations = self._generate_recommendations(valid, corr, etf_infos, div_score)

        return PortfolioAnalysis(
            tickers=tickers,
            correlation_matrix=corr,
            diversification_score=div_score,
            sector_exposure=sector_exposure,
            recommendations=recommendations,
            etf_infos=etf_infos,
        )

    @staticmethod
    def _fetch_closes(tickers: list[str], lookback_days: int) -> pd.DataFrame:
        if yf is None:
            return pd.DataFrame()
        try:
            from datetime import datetime, timedelta
            start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
            raw = yf.download(tickers, start=start, progress=False, auto_adjust=True)
            if raw is None or raw.empty:
                return pd.DataFrame()
            if isinstance(raw.columns, pd.MultiIndex):
                closes = raw["Close"]
                if isinstance(closes, pd.Series):
                    closes = closes.to_frame(name=tickers[0])
            else:
                closes = raw[["Close"]] if "Close" in raw.columns else raw
            return closes
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def _generate_recommendations(
        tickers: list[str],
        corr: pd.DataFrame,
        infos: list[ETFInfo],
        div_score: float,
    ) -> list[str]:
        recs: list[str] = []

        # Overall score
        if div_score >= 0.5:
            recs.append(f"Good diversification (score {div_score:.2f}/1.00). "
                        "Portfolio has low average pairwise correlation.")
        elif div_score >= 0.25:
            recs.append(f"Moderate diversification (score {div_score:.2f}/1.00). "
                        "Consider adding uncorrelated asset classes.")
        else:
            recs.append(f"Low diversification (score {div_score:.2f}/1.00). "
                        "Holdings are highly correlated — limited risk reduction benefit.")

        # Flag highly correlated pairs
        flagged: set[frozenset] = set()
        for i, t1 in enumerate(tickers):
            for t2 in tickers[i + 1:]:
                if t1 in corr.index and t2 in corr.columns:
                    c = corr.loc[t1, t2]
                    if abs(c) >= 0.85 and frozenset({t1, t2}) not in flagged:
                        recs.append(
                            f"High correlation ({c:.2f}) between {t1} and {t2} — "
                            "they likely move together; holding both adds limited diversification."
                        )
                        flagged.add(frozenset({t1, t2}))

        # High expense ratios
        for info in infos:
            if info.expense_ratio is not None and info.expense_ratio > 0.50:
                recs.append(
                    f"{info.ticker} has a high expense ratio ({info.expense_ratio:.2f}%). "
                    "Consider a lower-cost alternative if available."
                )

        # Missing fixed income
        categories = {info.category for info in infos}
        has_bonds = any("Bond" in c or "Fixed" in c for c in categories)
        has_equity = any("Blend" in c or "Growth" in c or "Equity" in c or "Sector" in c
                         for c in categories)
        if has_equity and not has_bonds and len(tickers) >= 3:
            recs.append(
                "No fixed income holdings detected. Adding a bond ETF (e.g. BND, AGG) "
                "can reduce overall portfolio volatility."
            )

        return recs
