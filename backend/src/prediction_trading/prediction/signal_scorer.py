"""Point-based signal scorer with indicator-category filtering.

This is the merged scoring engine — it covers:

* the six indicator categories from ``stock-prediction``
  (trend / momentum / volatility / volume / support / fundamental), each
  contributing integer points per rule (Golden Cross +2, MACD cross +2,
  RSI band +2, etc.), and
* the weighted 5-component model from ``automated-trading-systems``
  (still exposed as normalised ``components`` for backwards compatibility
  with the backtester).

Direction (bullish / bearish / neutral) and confidence (0..1) are derived
from the net point total. Every rule also emits a ``Factor`` so charts
and reports can render the human-readable signal list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd

from ..data_fetcher import MacroContext, NewsContext, SectorContext
from .factor import ALL_CATEGORIES, Direction, Factor, IndicatorCategory


@dataclass
class ScoredSignal:
    direction: Direction
    confidence: float
    factors: list[Factor] = field(default_factory=list)
    category_points: dict[str, int] = field(default_factory=dict)
    components: dict[str, float] = field(default_factory=dict)
    net_points: int = 0
    abs_points: int = 0

    @property
    def bullish_factors(self) -> list[Factor]:
        return [f for f in self.factors if f.direction == "bullish"]

    @property
    def bearish_factors(self) -> list[Factor]:
        return [f for f in self.factors if f.direction == "bearish"]

    def as_dict(self) -> dict:
        return {
            "direction": self.direction,
            "confidence": self.confidence,
            "net_points": self.net_points,
            "abs_points": self.abs_points,
            "category_points": self.category_points,
            "components": self.components,
            "factors": [f.as_dict() for f in self.factors],
        }


class SignalScorer:
    """Point-based scorer; rule points mirror the ``stock-prediction`` README.

    Example configuration::

        scorer = SignalScorer(
            categories=("trend", "momentum", "fundamental"),
            confidence_scale=10.0,
        )
    """

    # Normalised category weights for the (backward-compat) 5-component view
    DEFAULT_COMPONENT_WEIGHTS = {
        "trend": 0.25, "momentum": 0.25, "reversal": 0.20,
        "volatility": 0.15, "price_action": 0.15,
    }

    def __init__(
        self,
        *,
        categories: Iterable[str] | None = None,
        multi_timeframe_bonus: int = 2,
        confidence_scale: float = 10.0,
        weights: dict[str, float] | None = None,     # kept for API compat
    ) -> None:
        self.categories: tuple[IndicatorCategory, ...] = tuple(
            c for c in (categories or ALL_CATEGORIES) if c in ALL_CATEGORIES
        )
        self.multi_timeframe_bonus = multi_timeframe_bonus
        self.confidence_scale = max(1.0, confidence_scale)
        # `weights` is retained for drop-in compatibility with older callers
        # but point-based scoring is now primary.
        self._component_weights = dict(self.DEFAULT_COMPONENT_WEIGHTS)
        if weights:
            self._component_weights.update(weights)

    # ----------------------------------------------------------------- public
    def score(
        self,
        df: pd.DataFrame,
        *,
        weekly: pd.DataFrame | None = None,
        hourly_4h: pd.DataFrame | None = None,
        fundamentals: dict | None = None,
        news_context: NewsContext | None = None,
        macro_context: MacroContext | None = None,
        sector_context: SectorContext | None = None,
    ) -> ScoredSignal:
        if df.empty:
            return ScoredSignal(direction="neutral", confidence=0.0)

        # Pre-compute common slices once to avoid repeated .iloc[-1] calls
        self._last_row = df.iloc[-1]
        self._prev_row = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
        self._tail20 = df.tail(20)

        factors: list[Factor] = []

        if "trend" in self.categories:
            factors.extend(self._trend_factors(df))
        if "momentum" in self.categories:
            factors.extend(self._momentum_factors(df))
        if "volatility" in self.categories:
            factors.extend(self._volatility_factors(df))
        if "volume" in self.categories:
            factors.extend(self._volume_factors(df))
        if "support" in self.categories:
            factors.extend(self._support_factors(df))
        if "fundamental" in self.categories and fundamentals:
            factors.extend(self._fundamental_factors(fundamentals))
        if "news" in self.categories and news_context is not None:
            factors.extend(self._news_factors(news_context))
        if "macro" in self.categories and macro_context is not None:
            factors.extend(self._macro_factors(macro_context))
        if "sector" in self.categories and sector_context is not None:
            factors.extend(self._sector_factors(sector_context))

        net = sum(f.signed for f in factors)

        # Multi-timeframe confluence bonus
        if weekly is not None and not weekly.empty:
            wk = self._score_frame_points(weekly)
            if wk != 0 and ((net > 0 and wk > 0) or (net < 0 and wk < 0)):
                bonus = self.multi_timeframe_bonus
                factors.append(Factor(
                    category="trend", name="Weekly confluence",
                    direction="bullish" if wk > 0 else "bearish",
                    points=bonus,
                    detail="weekly timeframe agrees with daily",
                ))
                net += bonus if wk > 0 else -bonus

        # 4H timeframe confluence bonus
        if hourly_4h is not None and not hourly_4h.empty:
            h4 = self._score_frame_points(hourly_4h)
            if h4 != 0 and ((net > 0 and h4 > 0) or (net < 0 and h4 < 0)):
                h4_bonus = max(1, self.multi_timeframe_bonus - 1)
                factors.append(Factor(
                    category="trend", name="4H confluence",
                    direction="bullish" if h4 > 0 else "bearish",
                    points=h4_bonus,
                    detail="4-hour timeframe agrees with daily",
                ))
                net += h4_bonus if h4 > 0 else -h4_bonus

        abs_pts = sum(abs(f.signed) for f in factors) or 1
        confidence = float(min(1.0, abs(net) / self.confidence_scale))

        if net > 0:
            direction: Direction = "bullish"
        elif net < 0:
            direction = "bearish"
        else:
            direction = "neutral"

        # Aggregate per-category net points.
        cat_points: dict[str, int] = {c: 0 for c in ALL_CATEGORIES}
        for f in factors:
            cat_points[f.category] += f.signed

        # Build legacy 5-component view for the backtester's weighted engine.
        components = {
            "trend": self._norm(cat_points["trend"]),
            "momentum": self._norm(cat_points["momentum"]),
            "reversal": self._reversal_component(df) if "momentum" in self.categories else 0.0,
            "volatility": self._norm(cat_points["volatility"]),
            "price_action": self._price_action_component(df),
        }

        return ScoredSignal(
            direction=direction,
            confidence=confidence,
            factors=factors,
            category_points=cat_points,
            components=components,
            net_points=net,
            abs_points=abs_pts,
        )

    # ----------------------------------------------------------- trend rules
    def _trend_factors(self, df: pd.DataFrame) -> list[Factor]:
        row = getattr(self, "_last_row", df.iloc[-1])
        prev = getattr(self, "_prev_row", df.iloc[-2] if len(df) >= 2 else row)
        close = self._v(row["Close"])
        sma50 = self._v(row.get("SMA50"))
        sma200 = self._v(row.get("SMA200"))
        ema12 = self._v(row.get("EMA12"))
        ema26 = self._v(row.get("EMA26"))

        facs: list[Factor] = []
        # Price vs SMAs
        if sma50 and close > sma50:
            facs.append(Factor("trend", "Price above SMA50", "bullish", 1,
                               f"${close:.2f} > ${sma50:.2f}"))
        elif sma50 and close < sma50:
            facs.append(Factor("trend", "Price below SMA50", "bearish", 1,
                               f"${close:.2f} < ${sma50:.2f}"))
        if sma200 and close > sma200:
            facs.append(Factor("trend", "Price above SMA200", "bullish", 1,
                               f"${close:.2f} > ${sma200:.2f}"))
        elif sma200 and close < sma200:
            facs.append(Factor("trend", "Price below SMA200", "bearish", 1,
                               f"${close:.2f} < ${sma200:.2f}"))

        # Golden / Death Cross (detected on 1–5 bar window to be robust)
        if sma50 and sma200:
            prev_50 = self._v(prev.get("SMA50"))
            prev_200 = self._v(prev.get("SMA200"))
            if prev_50 and prev_200:
                if sma50 > sma200 and prev_50 <= prev_200:
                    facs.append(Factor("trend", "Golden Cross", "bullish", 2,
                                       "SMA50 crossed above SMA200"))
                elif sma50 < sma200 and prev_50 >= prev_200:
                    facs.append(Factor("trend", "Death Cross", "bearish", 2,
                                       "SMA50 crossed below SMA200"))

        # MACD crossover event
        macd = self._v(row.get("MACD"))
        macd_sig = self._v(row.get("MACD_signal"))
        if macd and macd_sig:
            prev_macd = self._v(prev.get("MACD"))
            prev_sig = self._v(prev.get("MACD_signal"))
            if prev_macd and prev_sig:
                if macd > macd_sig and prev_macd <= prev_sig:
                    facs.append(Factor("trend", "MACD bullish crossover", "bullish", 2,
                                       "MACD crossed above signal"))
                elif macd < macd_sig and prev_macd >= prev_sig:
                    facs.append(Factor("trend", "MACD bearish crossover", "bearish", 2,
                                       "MACD crossed below signal"))
                elif macd > macd_sig:
                    facs.append(Factor("trend", "MACD above signal", "bullish", 1))
                elif macd < macd_sig:
                    facs.append(Factor("trend", "MACD below signal", "bearish", 1))

        # EMA12 vs EMA26
        if ema12 and ema26:
            if ema12 > ema26:
                facs.append(Factor("trend", "EMA12 above EMA26", "bullish", 1))
            else:
                facs.append(Factor("trend", "EMA12 below EMA26", "bearish", 1))
        return facs

    # --------------------------------------------------------- momentum rules
    def _momentum_factors(self, df: pd.DataFrame) -> list[Factor]:
        row = getattr(self, "_last_row", df.iloc[-1])
        prev = getattr(self, "_prev_row", df.iloc[-2] if len(df) >= 2 else row)
        facs: list[Factor] = []

        rsi = self._v(row.get("RSI"))
        if rsi:
            if rsi < 30:
                facs.append(Factor("momentum", "RSI oversold", "bullish", 2,
                                   f"RSI={rsi:.1f} < 30"))
            elif rsi > 70:
                facs.append(Factor("momentum", "RSI overbought", "bearish", 2,
                                   f"RSI={rsi:.1f} > 70"))
            elif rsi > 50:
                facs.append(Factor("momentum", "RSI above midline", "bullish", 1,
                                   f"RSI={rsi:.1f} > 50"))
            elif rsi < 50:
                facs.append(Factor("momentum", "RSI below midline", "bearish", 1,
                                   f"RSI={rsi:.1f} < 50"))

        k = self._v(row.get("Stoch_K"))
        d = self._v(row.get("Stoch_D"))
        prev_k = self._v(prev.get("Stoch_K"))
        prev_d = self._v(prev.get("Stoch_D"))
        if k and d:
            if prev_k and prev_d:
                if k > d and prev_k <= prev_d:
                    facs.append(Factor("momentum", "Stochastic bullish cross",
                                       "bullish", 1, f"%K={k:.1f} crossed %D"))
                elif k < d and prev_k >= prev_d:
                    facs.append(Factor("momentum", "Stochastic bearish cross",
                                       "bearish", 1, f"%K={k:.1f} crossed %D"))
            if k < 20:
                facs.append(Factor("momentum", "Stochastic oversold", "bullish", 1,
                                   f"%K={k:.1f} < 20"))
            elif k > 80:
                facs.append(Factor("momentum", "Stochastic overbought", "bearish", 1,
                                   f"%K={k:.1f} > 80"))
        return facs

    # ------------------------------------------------------ volatility rules
    def _volatility_factors(self, df: pd.DataFrame) -> list[Factor]:
        row = getattr(self, "_last_row", df.iloc[-1])
        facs: list[Factor] = []
        close = self._v(row["Close"])
        upper = self._v(row.get("BB_upper"))
        lower = self._v(row.get("BB_lower"))

        if upper and close >= upper:
            facs.append(Factor("volatility", "Price above BB upper", "bearish", 1,
                               f"${close:.2f} ≥ ${upper:.2f}"))
        if lower and close <= lower:
            facs.append(Factor("volatility", "Price below BB lower", "bullish", 1,
                               f"${close:.2f} ≤ ${lower:.2f}"))

        atr = self._v(row.get("ATR"))
        tail20 = getattr(self, "_tail20", df.tail(20))
        atr_series = tail20["ATR"].dropna() if "ATR" in tail20.columns else pd.Series(dtype=float)
        atr_mean = float(atr_series.mean() or 0.0)
        if atr and atr_mean:
            ratio = atr / atr_mean
            if ratio > 1.3:
                facs.append(Factor("volatility", "Elevated ATR (high vol)",
                                   "bearish", 1,
                                   f"ATR={atr:.2f} ({ratio:.2f}× 20d mean)"))
            elif ratio < 0.8:
                facs.append(Factor("volatility", "Low ATR (calm)",
                                   "bullish", 1,
                                   f"ATR={atr:.2f} ({ratio:.2f}× 20d mean)"))
        return facs

    # ---------------------------------------------------------- volume rules
    def _volume_factors(self, df: pd.DataFrame) -> list[Factor]:
        facs: list[Factor] = []
        tail20 = getattr(self, "_tail20", df.tail(20))
        if "OBV" in df and df["OBV"].notna().any():
            obv_tail = tail20["OBV"]
            if obv_tail.iloc[-1] > obv_tail.iloc[0]:
                facs.append(Factor("volume", "OBV rising", "bullish", 1,
                                   "on-balance volume trending up"))
            elif obv_tail.iloc[-1] < obv_tail.iloc[0]:
                facs.append(Factor("volume", "OBV falling", "bearish", 1,
                                   "on-balance volume trending down"))

        if "VolumeSpike" in df and len(df) >= 2 and bool(df["VolumeSpike"].iloc[-1]):
            close = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]
            if close >= prev_close:
                facs.append(Factor("volume", "Volume spike on up day",
                                   "bullish", 1, "volume > 20d mean + 2σ"))
            else:
                facs.append(Factor("volume", "Volume spike on down day",
                                   "bearish", 1, "volume > 20d mean + 2σ"))
        return facs

    # --------------------------------------------------------- support rules
    def _support_factors(self, df: pd.DataFrame) -> list[Factor]:
        from ..indicators.levels import SupportResistance

        facs: list[Factor] = []
        row = getattr(self, "_last_row", df.iloc[-1])
        close = self._v(row["Close"])
        # Classical pivot uses prior-day OHLC per DESIGN.md §4.3
        prior = df.iloc[-2] if len(df) >= 2 else row
        piv = SupportResistance.pivot_points(
            float(prior["High"]), float(prior["Low"]), float(prior["Close"]),
        )
        if close > piv.pp:
            facs.append(Factor("support", "Price above Pivot", "bullish", 1,
                               f"${close:.2f} > PP ${piv.pp:.2f}"))
        elif close < piv.pp:
            facs.append(Factor("support", "Price below Pivot", "bearish", 1,
                               f"${close:.2f} < PP ${piv.pp:.2f}"))

        # Trendline break / hold
        tl = SupportResistance.trendlines(df, window=5)
        if "support" in tl:
            slope, intercept = tl["support"]
            projected = slope * (len(df) - 1) + intercept
            if slope > 0 and close > projected:
                facs.append(Factor("support", "Rising support holding", "bullish", 1,
                                   f"above trendline ${projected:.2f}"))
            elif close < projected:
                facs.append(Factor("support", "Support broken", "bearish", 1,
                                   f"below trendline ${projected:.2f}"))
        return facs

    # ---------------------------------------------------- fundamental rules
    def _fundamental_factors(self, fund: dict) -> list[Factor]:
        facs: list[Factor] = []

        def rule(key: str, *, bull_name: str, bear_name: str,
                 bull_fn=None, bear_fn=None, pts: int = 1,
                 fmt=lambda v: f"{v}") -> None:
            val = fund.get(key)
            if val is None:
                return
            try:
                v = float(val)
            except (TypeError, ValueError):
                return
            if bull_fn and bull_fn(v):
                facs.append(Factor("fundamental", bull_name, "bullish", pts, fmt(v)))
            elif bear_fn and bear_fn(v):
                facs.append(Factor("fundamental", bear_name, "bearish", pts, fmt(v)))

        rule("trailingPE",
             bull_name="P/E attractive", bear_name="P/E expensive",
             bull_fn=lambda v: 0 < v < 15,
             bear_fn=lambda v: v > 35,
             fmt=lambda v: f"P/E={v:.2f}")
        rule("pegRatio",
             bull_name="PEG undervalued", bear_name="PEG overvalued",
             bull_fn=lambda v: 0 < v < 1,
             bear_fn=lambda v: v > 3,
             fmt=lambda v: f"PEG={v:.2f}")
        rule("revenueGrowth",
             bull_name="Revenue growth strong", bear_name="Revenue declining",
             bull_fn=lambda v: v > 0.10,
             bear_fn=lambda v: v < 0.0,
             fmt=lambda v: f"YoY={v*100:.1f}%")
        rule("earningsGrowth",
             bull_name="Earnings growth strong", bear_name="Earnings declining",
             bull_fn=lambda v: v > 0.15,
             bear_fn=lambda v: v < 0.0,
             fmt=lambda v: f"YoY={v*100:.1f}%")
        rule("profitMargins",
             bull_name="Strong net margin", bear_name="Negative net margin",
             bull_fn=lambda v: v > 0.15,
             bear_fn=lambda v: v < 0.0,
             fmt=lambda v: f"net={v*100:.1f}%")
        rule("returnOnEquity",
             bull_name="Strong ROE", bear_name="Negative ROE",
             bull_fn=lambda v: v > 0.15,
             bear_fn=lambda v: v < 0.0,
             fmt=lambda v: f"ROE={v*100:.1f}%")
        rule("debtToEquity",
             bull_name="Healthy debt/equity", bear_name="Elevated debt/equity",
             bull_fn=lambda v: v < 50,        # yfinance gives D/E in percent
             bear_fn=lambda v: v > 200,
             fmt=lambda v: f"D/E={v:.1f}")
        rule("currentRatio",
             bull_name="Strong liquidity", bear_name="Weak liquidity",
             bull_fn=lambda v: v >= 1.5,
             bear_fn=lambda v: v < 1.0,
             fmt=lambda v: f"CR={v:.2f}")
        rule("priceToBook",
             bull_name="P/B attractive", bear_name="P/B expensive",
             bull_fn=lambda v: 0 < v < 2,
             bear_fn=lambda v: v > 8,
             fmt=lambda v: f"P/B={v:.2f}")
        return facs

    # ------------------------------------------------------------ news rules
    def _news_factors(self, ctx: NewsContext) -> list[Factor]:
        facs: list[Factor] = []
        s = ctx.sentiment_score
        if s > 0.3:
            facs.append(Factor("news", "Positive news sentiment", "bullish", 2,
                               f"score={s:.2f}, {ctx.article_count} articles"))
        elif s < -0.3:
            facs.append(Factor("news", "Negative news sentiment", "bearish", 2,
                               f"score={s:.2f}, {ctx.article_count} articles"))
        if ctx.earnings_beat:
            facs.append(Factor("news", "Earnings beat", "bullish", 2,
                               "recent EPS actual > estimate"))
        elif ctx.earnings_miss:
            facs.append(Factor("news", "Earnings miss", "bearish", 2,
                               "recent EPS actual < estimate"))
        days = ctx.earnings_upcoming_days
        if days is not None and days <= 7:
            facs.append(Factor("news", "Earnings risk", "neutral", 0,
                               f"earnings in {days}d — binary event risk"))
        return facs

    # ------------------------------------------------------------ macro rules
    def _macro_factors(self, ctx: MacroContext) -> list[Factor]:
        facs: list[Factor] = []
        vix = ctx.vix
        if vix is not None:
            if vix < 15:
                facs.append(Factor("macro", "Low volatility regime", "bullish", 1,
                                   f"VIX={vix:.1f} < 15"))
            elif 25 <= vix <= 35:
                facs.append(Factor("macro", "Elevated market fear", "bearish", 1,
                                   f"VIX={vix:.1f}"))
            elif vix > 35:
                facs.append(Factor("macro", "Market panic (VIX >35)", "bearish", 2,
                                   f"VIX={vix:.1f}"))
        spread = ctx.yield_spread
        if spread is not None:
            if spread > 0.2:
                facs.append(Factor("macro", "Normal yield curve", "bullish", 1,
                                   f"10Y-2Y={spread:.2f}%"))
            elif spread < -0.2:
                facs.append(Factor("macro", "Inverted yield curve", "bearish", 1,
                                   f"10Y-2Y={spread:.2f}%"))
        if ctx.spy_above_sma50 is True:
            facs.append(Factor("macro", "Broad market uptrend", "bullish", 1,
                               "SPY above 50-day SMA"))
        elif ctx.spy_above_sma50 is False:
            facs.append(Factor("macro", "Broad market downtrend", "bearish", 1,
                               "SPY below 50-day SMA"))

        if ctx.indexes:
            above_50 = sum(1 for idx in ctx.indexes if idx.above_sma50 is True)
            above_200 = sum(1 for idx in ctx.indexes if idx.above_sma200 is True)
            if above_50 >= 2:
                facs.append(Factor("macro", "Market breadth above SMA50", "bullish", 1,
                                   f"{above_50}/3 indexes above 50d SMA"))
            elif above_50 == 0:
                facs.append(Factor("macro", "Market breadth below SMA50", "bearish", 1,
                                   "All 3 indexes below 50d SMA"))
            if above_200 == 3:
                facs.append(Factor("macro", "Full market above SMA200", "bullish", 1,
                                   "DOW, NASDAQ & S&P 500 all above 200d SMA"))
            elif above_200 == 0:
                facs.append(Factor("macro", "Full market below SMA200", "bearish", 1,
                                   "All 3 indexes below 200d SMA"))

        return facs

    # ----------------------------------------------------------- sector rules
    def _sector_factors(self, ctx: SectorContext) -> list[Factor]:
        facs: list[Factor] = []
        vs = ctx.vs_sector
        if vs is not None:
            if vs > 0.03:
                facs.append(Factor("sector", "Outperforming sector", "bullish", 1,
                                   f"stock +{vs*100:.1f}% vs {ctx.sector_etf}"))
            elif vs < -0.03:
                facs.append(Factor("sector", "Underperforming sector", "bearish", 1,
                                   f"stock {vs*100:.1f}% vs {ctx.sector_etf}"))
        sv = ctx.sector_vs_spy
        if sv is not None:
            if sv > 0.02:
                facs.append(Factor("sector", "Sector leading market", "bullish", 1,
                                   f"{ctx.sector_etf} +{sv*100:.1f}% vs SPY"))
            elif sv < -0.02:
                facs.append(Factor("sector", "Sector lagging market", "bearish", 1,
                                   f"{ctx.sector_etf} {sv*100:.1f}% vs SPY"))
        return facs

    # ---------------------------------------------------------- helpers
    @staticmethod
    def _v(value) -> float:
        if value is None:
            return 0.0
        try:
            fv = float(value)
            if np.isnan(fv):
                return 0.0
            return fv
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _norm(points: int) -> float:
        return float(np.clip(points / 5.0, -1.0, 1.0))

    def _score_frame_points(self, df: pd.DataFrame) -> int:
        """Lightweight point sum used for weekly/daily confluence check."""
        factors: list[Factor] = []
        if "trend" in self.categories:
            factors.extend(self._trend_factors(df))
        if "momentum" in self.categories:
            factors.extend(self._momentum_factors(df))
        return sum(f.signed for f in factors)

    def _reversal_component(self, df: pd.DataFrame) -> float:
        if "RSI" not in df.columns:
            return 0.0
        tail = df.tail(20)
        if len(tail) < 20:
            return 0.0
        price_trend = float(tail["Close"].iloc[-1] - tail["Close"].iloc[0])
        rsi_trend = float(tail["RSI"].iloc[-1] - tail["RSI"].iloc[0])
        if price_trend < 0 and rsi_trend > 0:
            return 0.5
        if price_trend > 0 and rsi_trend < 0:
            return -0.5
        return 0.0

    def _price_action_component(self, df: pd.DataFrame) -> float:
        tail = df.tail(10)
        if len(tail) < 5:
            return 0.0
        highs = tail["High"]; lows = tail["Low"]
        hh = all(highs.iloc[i] >= highs.iloc[i - 1] for i in range(-3, 0))
        hl = all(lows.iloc[i] >= lows.iloc[i - 1] for i in range(-3, 0))
        lh = all(highs.iloc[i] <= highs.iloc[i - 1] for i in range(-3, 0))
        ll = all(lows.iloc[i] <= lows.iloc[i - 1] for i in range(-3, 0))
        score = 0.0
        if hh and hl: score += 0.6
        if lh and ll: score -= 0.6
        return float(np.clip(score, -1.0, 1.0))
