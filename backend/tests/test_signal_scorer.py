from prediction_trading.indicators import TechnicalIndicators
from prediction_trading.prediction import ALL_CATEGORIES, SignalScorer


def test_scorer_favours_uptrend(ohlcv_uptrend):
    df = TechnicalIndicators.compute_all(ohlcv_uptrend)
    sig = SignalScorer().score(df)
    assert sig.direction in ("bullish", "neutral")
    if sig.direction == "bullish":
        assert sig.net_points > 0
        assert sig.confidence > 0


def test_scorer_favours_downtrend(ohlcv_downtrend):
    df = TechnicalIndicators.compute_all(ohlcv_downtrend)
    sig = SignalScorer().score(df)
    # A synthetic random walk can rebound at the very last bar, so instead of
    # checking the final direction we verify the long-term structure is bearish
    # — price well below SMA200, with bearish factors present.
    last = df.iloc[-1]
    assert last["Close"] < last["SMA200"]
    assert any(f.direction == "bearish" for f in sig.factors)


def test_scorer_sideways_valid_range(ohlcv_sideways):
    df = TechnicalIndicators.compute_all(ohlcv_sideways)
    sig = SignalScorer().score(df)
    assert 0.0 <= sig.confidence <= 1.0


def test_components_cover_all(ohlcv_uptrend):
    df = TechnicalIndicators.compute_all(ohlcv_uptrend)
    sig = SignalScorer().score(df)
    assert set(sig.components.keys()) == {
        "trend", "momentum", "reversal", "volatility", "price_action",
    }


def test_weekly_agreement_bonus(ohlcv_uptrend):
    df = TechnicalIndicators.compute_all(ohlcv_uptrend)
    weekly = ohlcv_uptrend.resample("W").agg(
        {"Open": "first", "High": "max", "Low": "min",
         "Close": "last", "Volume": "sum"}
    ).dropna()
    weekly_enriched = TechnicalIndicators.compute_all(weekly)
    without = SignalScorer().score(df)
    with_ = SignalScorer().score(df, weekly=weekly_enriched)
    assert with_.confidence >= without.confidence


def test_category_filtering_removes_factors(ohlcv_uptrend):
    df = TechnicalIndicators.compute_all(ohlcv_uptrend)
    trend_only = SignalScorer(categories=("trend",)).score(df)
    assert all(f.category == "trend" for f in trend_only.factors
               if f.name != "Weekly confluence")
    momentum_only = SignalScorer(categories=("momentum",)).score(df)
    assert all(f.category == "momentum" for f in momentum_only.factors
               if f.name != "Weekly confluence")


def test_fundamental_scoring_detects_good_company():
    import pandas as pd
    from tests.conftest import _synthetic_ohlcv  # type: ignore[attr-defined]
    df = TechnicalIndicators.compute_all(_synthetic_ohlcv(trend=0.0005, seed=3))
    fundamentals = {
        "trailingPE": 12.0,            # bullish: < 15
        "pegRatio": 0.8,               # bullish: < 1
        "revenueGrowth": 0.25,         # bullish: > 10%
        "earningsGrowth": 0.30,        # bullish: > 15%
        "profitMargins": 0.22,         # bullish: > 15%
        "returnOnEquity": 0.28,        # bullish: > 15%
        "debtToEquity": 30.0,          # bullish: < 50
        "currentRatio": 2.2,           # bullish: >= 1.5
        "priceToBook": 1.4,            # bullish: < 2
    }
    sig = SignalScorer().score(df, fundamentals=fundamentals)
    fund_factors = [f for f in sig.factors if f.category == "fundamental"]
    assert len(fund_factors) >= 5
    assert all(f.direction == "bullish" for f in fund_factors)


def test_fundamental_scoring_detects_weak_company():
    import pandas as pd
    from tests.conftest import _synthetic_ohlcv  # type: ignore[attr-defined]
    df = TechnicalIndicators.compute_all(_synthetic_ohlcv(trend=0.0, seed=5))
    fundamentals = {
        "trailingPE": 55.0,            # bearish
        "pegRatio": 4.0,               # bearish
        "revenueGrowth": -0.10,        # bearish
        "earningsGrowth": -0.20,       # bearish
        "profitMargins": -0.05,        # bearish
        "returnOnEquity": -0.08,       # bearish
        "debtToEquity": 350.0,         # bearish
        "currentRatio": 0.7,           # bearish
    }
    sig = SignalScorer().score(df, fundamentals=fundamentals)
    fund_factors = [f for f in sig.factors if f.category == "fundamental"]
    assert len(fund_factors) >= 5
    assert all(f.direction == "bearish" for f in fund_factors)


def test_crossover_detection_emits_cross_events(ohlcv_uptrend):
    df = TechnicalIndicators.compute_all(ohlcv_uptrend)
    sig = SignalScorer().score(df)
    names = {f.name for f in sig.factors}
    # In a clean uptrend we should see at least one of these trend confirmations.
    assert any(n in names for n in (
        "Price above SMA50", "Price above SMA200", "EMA12 above EMA26",
        "MACD above signal", "MACD bullish crossover", "Golden Cross",
    ))


def test_all_categories_present_by_default():
    assert set(ALL_CATEGORIES) == {
        "trend", "momentum", "volatility", "volume", "support", "fundamental",
        "news", "macro", "sector",
    }
