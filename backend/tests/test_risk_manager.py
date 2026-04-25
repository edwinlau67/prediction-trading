from datetime import datetime

import pytest

from prediction_trading.prediction.predictor import Prediction
from prediction_trading.trading.portfolio import Portfolio, Position
from prediction_trading.trading.risk_manager import RiskManager


_TS = datetime(2024, 6, 1, 10, 0)


def _pred(direction="bullish", confidence=0.60, price=100.0, ticker="AAPL") -> Prediction:
    return Prediction(
        ticker=ticker, direction=direction, confidence=confidence,
        current_price=price,
    )


def _risk(**kwargs) -> RiskManager:
    defaults = dict(
        max_positions=5, max_position_size_pct=0.05, max_daily_loss_pct=0.02,
        min_risk_reward=1.5, stop_loss_atr_mult=2.0, take_profit_atr_mult=3.0,
        min_confidence=0.40,
    )
    defaults.update(kwargs)
    return RiskManager(**defaults)


def _portfolio(capital: float = 10_000.0) -> Portfolio:
    return Portfolio(initial_capital=capital)


def test_default_min_confidence_is_0_40():
    rm = RiskManager()
    assert rm.min_confidence == 0.40


def test_neutral_direction_returns_none():
    rm = _risk()
    p = _portfolio()
    assert rm.evaluate(_pred(direction="neutral"), portfolio=p, atr=2.0, timestamp=_TS) is None


def test_below_confidence_gate():
    rm = _risk(min_confidence=0.50)
    p = _portfolio()
    assert rm.evaluate(_pred(confidence=0.40), portfolio=p, atr=2.0, timestamp=_TS) is None


def test_above_confidence_gate_produces_proposal():
    rm = _risk()
    p = _portfolio(100_000.0)
    proposal = rm.evaluate(_pred(confidence=0.60), portfolio=p, atr=2.0, timestamp=_TS)
    assert proposal is not None
    assert proposal.side == "long"


def test_bearish_produces_short_proposal():
    rm = _risk()
    p = _portfolio(100_000.0)
    proposal = rm.evaluate(_pred(direction="bearish", confidence=0.55), portfolio=p,
                           atr=2.0, timestamp=_TS)
    assert proposal is not None
    assert proposal.side == "short"


def test_max_positions_gate():
    rm = _risk(max_positions=1)
    p = _portfolio(100_000.0)
    existing = Position("TSLA", "long", 10, 100.0, _TS, 90.0, 115.0)
    p.positions["TSLA"] = existing
    assert rm.evaluate(_pred(ticker="AAPL"), portfolio=p, atr=2.0, timestamp=_TS) is None


def test_duplicate_ticker_gate():
    rm = _risk()
    p = _portfolio(100_000.0)
    p.positions["AAPL"] = Position("AAPL", "long", 10, 100.0, _TS, 90.0, 115.0)
    assert rm.evaluate(_pred(ticker="AAPL"), portfolio=p, atr=2.0, timestamp=_TS) is None


def test_invalid_atr_returns_none():
    rm = _risk()
    p = _portfolio(100_000.0)
    assert rm.evaluate(_pred(), portfolio=p, atr=0.0, timestamp=_TS) is None
    assert rm.evaluate(_pred(), portfolio=p, atr=-1.0, timestamp=_TS) is None


def test_min_risk_reward_gate():
    rm = _risk(min_risk_reward=5.0, stop_loss_atr_mult=2.0, take_profit_atr_mult=3.0)
    p = _portfolio(100_000.0)
    # R:R = 3/2 = 1.5, which is < 5.0
    assert rm.evaluate(_pred(), portfolio=p, atr=2.0, timestamp=_TS) is None


def test_daily_loss_gate():
    rm = _risk(max_daily_loss_pct=0.01)
    p = _portfolio(10_000.0)
    # Simulate start equity recorded then drawdown
    rm._day_start_equity[_TS.strftime("%Y-%m-%d")] = 10_000.0
    p.equity_curve.append((_TS, 9_850.0))  # 1.5% drawdown > 1% limit
    assert rm.evaluate(_pred(), portfolio=p, atr=2.0, timestamp=_TS) is None


def test_proposal_stops_and_target():
    rm = _risk(stop_loss_atr_mult=2.0, take_profit_atr_mult=3.0)
    p = _portfolio(100_000.0)
    proposal = rm.evaluate(_pred(price=100.0), portfolio=p, atr=5.0, timestamp=_TS)
    assert proposal is not None
    assert proposal.stop_loss == pytest.approx(90.0)   # 100 - 2*5
    assert proposal.take_profit == pytest.approx(115.0)  # 100 + 3*5
