"""Tests for the automated trading engine.

Uses a fake data fetcher and a stub predictor to keep everything offline
and deterministic — no yfinance, no Anthropic, no wall-clock scheduler.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from prediction_trading.data_fetcher import MarketData
from prediction_trading.prediction import Prediction
from prediction_trading.trading import (
    AutoTrader,
    MarketHours,
    Order,
    PaperBroker,
    Portfolio,
    RecordingBroker,
    RiskManager,
    StateStore,
)


# -------------------------------------------------------------------- fakes
class FakeDataFetcher:
    """Return a preloaded OHLCV frame so tests never hit the network."""

    def __init__(self, ohlcv: pd.DataFrame) -> None:
        self.ohlcv = ohlcv

    def fetch(self, ticker: str, *, lookback_days: int = 365,
              include_fundamentals: bool = True) -> MarketData:
        df = self.ohlcv.copy()
        return MarketData(
            ticker=ticker.upper(), ohlcv=df,
            current_price=float(df["Close"].iloc[-1]),
            fundamentals={},
        )

    def fetch_history(self, ticker: str, **kwargs) -> pd.DataFrame:
        return self.ohlcv.copy()


@dataclass
class StubPrediction:
    direction: str
    confidence: float
    price_target: float | None = None


class StubPredictor:
    """Always emits the same Prediction — makes risk-gate tests deterministic."""

    def __init__(self, direction: str = "bullish", confidence: float = 0.9) -> None:
        self.direction = direction
        self.confidence = confidence
        self.calls: list[str] = []

    def predict(self, *, ticker: str, df, current_price: float,
                weekly=None, fundamentals=None) -> Prediction:
        self.calls.append(ticker)
        return Prediction(
            ticker=ticker,
            direction=self.direction,       # type: ignore[arg-type]
            confidence=self.confidence,
            current_price=current_price,
            price_target=current_price * 1.05,
        )


# -------------------------------------------------------------------- tests
def test_paper_broker_open_and_close_roundtrip():
    portfolio = Portfolio(initial_capital=10_000.0, commission_per_trade=1.0)
    broker = PaperBroker(portfolio, quote_fn=lambda t: 100.0)

    order = Order(ticker="AAPL", side="long", quantity=10,
                  stop_loss=95.0, take_profit=110.0)
    fill = broker.place_order(order)

    assert fill is not None
    assert fill.fill_price == 100.0
    assert "AAPL" in portfolio.positions

    # raise quote and close for profit
    broker._quote_fn = lambda t: 110.0
    trade = broker.close_position("AAPL", reason="take_profit")
    assert trade is not None
    assert trade.pnl == 10 * (110 - 100) - 2 * 1.0
    assert "AAPL" not in portfolio.positions


def test_paper_broker_rejects_duplicate_position():
    portfolio = Portfolio(initial_capital=10_000.0)
    broker = PaperBroker(portfolio, quote_fn=lambda t: 100.0)
    broker.place_order(Order(ticker="AAPL", side="long", quantity=5))
    second = broker.place_order(Order(ticker="AAPL", side="long", quantity=5))
    assert second is None


def test_paper_broker_applies_slippage():
    portfolio = Portfolio(initial_capital=10_000.0)
    broker = PaperBroker(portfolio, quote_fn=lambda t: 100.0, slippage_bps=10)  # 0.1%
    fill = broker.place_order(Order(ticker="AAPL", side="long", quantity=10))
    assert fill is not None
    assert fill.fill_price == pytest.approx(100.1)


def test_state_store_roundtrip(tmp_path: Path):
    now = datetime(2024, 1, 2, 15, 30)
    portfolio = Portfolio(initial_capital=10_000.0, commission_per_trade=1.0)
    portfolio.mark(now, {})
    broker = PaperBroker(portfolio, quote_fn=lambda t: 100.0)
    broker.place_order(Order(ticker="AAPL", side="long", quantity=5,
                              stop_loss=95.0, take_profit=110.0))
    broker.close_position("AAPL", quote=110.0, when=now + timedelta(days=1))

    store = StateStore(tmp_path / "state.json")
    store.save(portfolio)

    restored = store.load()
    assert restored.initial_capital == 10_000.0
    assert len(restored.closed_trades) == 1
    assert restored.closed_trades[0].ticker == "AAPL"
    assert restored.closed_trades[0].pnl == pytest.approx(
        portfolio.closed_trades[0].pnl
    )


def test_auto_trader_opens_trade_when_risk_approves(ohlcv_uptrend):
    data = FakeDataFetcher(ohlcv_uptrend)
    predictor = StubPredictor(direction="bullish", confidence=0.9)
    risk = RiskManager(
        max_positions=3, max_position_size_pct=0.2,
        max_daily_loss_pct=0.9, min_risk_reward=1.0,
        min_confidence=0.1,
    )
    portfolio = Portfolio(initial_capital=10_000.0, commission_per_trade=1.0)
    last_close = float(ohlcv_uptrend["Close"].iloc[-1])
    broker = PaperBroker(portfolio, quote_fn=lambda t: last_close)

    trader = AutoTrader(
        tickers=["AAPL"], predictor=predictor, risk=risk,
        broker=broker, portfolio=portfolio, data_fetcher=data,
    )
    report = trader.run_once()

    assert "AAPL" in portfolio.positions
    actions = [a.action for a in report.actions]
    assert "open" in actions
    open_action = next(a for a in report.actions if a.action == "open")
    assert open_action.direction == "long"
    assert open_action.quantity == portfolio.positions["AAPL"].quantity


def test_auto_trader_dry_run_submits_no_order(ohlcv_uptrend):
    data = FakeDataFetcher(ohlcv_uptrend)
    predictor = StubPredictor(direction="bullish", confidence=0.9)
    risk = RiskManager(
        max_positions=3, max_position_size_pct=0.2,
        max_daily_loss_pct=0.9, min_risk_reward=1.0,
        min_confidence=0.1,
    )
    portfolio = Portfolio(initial_capital=10_000.0)
    last_close = float(ohlcv_uptrend["Close"].iloc[-1])
    broker = RecordingBroker(quote_source={"AAPL": last_close})

    trader = AutoTrader(
        tickers=["AAPL"], predictor=predictor, risk=risk,
        broker=broker, portfolio=portfolio, data_fetcher=data,
        dry_run=True,
    )
    report = trader.run_once()

    assert broker.orders == []
    assert not portfolio.positions
    skip_reasons = [a.reason for a in report.actions if a.action == "skip"]
    assert any("dry-run" in r for r in skip_reasons)


def test_auto_trader_closes_on_stop_loss(ohlcv_uptrend):
    data = FakeDataFetcher(ohlcv_uptrend)
    predictor = StubPredictor(direction="neutral", confidence=0.0)
    risk = RiskManager(min_confidence=0.1)
    portfolio = Portfolio(initial_capital=10_000.0, commission_per_trade=1.0)
    entry_price = float(ohlcv_uptrend["Close"].iloc[-1])
    portfolio.cash = 10_000.0
    # seed an open long position that will breach stop once quote drops
    from prediction_trading.trading.portfolio import Position
    portfolio.open(Position(
        ticker="AAPL", side="long", quantity=10,
        entry_price=entry_price,
        entry_time=datetime(2024, 1, 1),
        stop_loss=entry_price * 1.5,   # above current price → instant stop
        take_profit=entry_price * 2.0,
    ))

    broker = PaperBroker(portfolio, quote_fn=lambda t: entry_price)
    trader = AutoTrader(
        tickers=["AAPL"], predictor=predictor, risk=risk,
        broker=broker, portfolio=portfolio, data_fetcher=data,
    )
    report = trader.run_once()

    assert "AAPL" not in portfolio.positions
    close_actions = [a for a in report.actions if a.action == "close"]
    assert close_actions and close_actions[0].reason == "stop_loss"


def test_auto_trader_writes_trade_log_and_state(tmp_path: Path, ohlcv_uptrend):
    data = FakeDataFetcher(ohlcv_uptrend)
    predictor = StubPredictor(direction="bullish", confidence=0.9)
    risk = RiskManager(
        max_positions=3, max_position_size_pct=0.2,
        max_daily_loss_pct=0.9, min_risk_reward=1.0,
        min_confidence=0.1,
    )
    portfolio = Portfolio(initial_capital=10_000.0, commission_per_trade=1.0)
    last_close = float(ohlcv_uptrend["Close"].iloc[-1])
    broker = PaperBroker(portfolio, quote_fn=lambda t: last_close)
    store = StateStore(tmp_path / "state.json")
    trade_log = tmp_path / "trades.csv"

    trader = AutoTrader(
        tickers=["AAPL"], predictor=predictor, risk=risk,
        broker=broker, portfolio=portfolio, data_fetcher=data,
        state_store=store, trade_log=trade_log,
    )
    trader.run_once()

    assert store.exists()
    assert trade_log.exists()
    # CSV should have at least a header + one open row
    lines = trade_log.read_text().strip().splitlines()
    assert len(lines) >= 2
    assert "timestamp" in lines[0]


def test_auto_trader_skips_cycle_outside_market_hours(ohlcv_uptrend):
    data = FakeDataFetcher(ohlcv_uptrend)
    predictor = StubPredictor(direction="bullish", confidence=0.9)
    risk = RiskManager(min_confidence=0.1)
    portfolio = Portfolio(initial_capital=10_000.0)
    broker = PaperBroker(portfolio, quote_fn=lambda t: 100.0)
    hours = MarketHours()

    trader = AutoTrader(
        tickers=["AAPL"], predictor=predictor, risk=risk,
        broker=broker, portfolio=portfolio, data_fetcher=data,
        market_hours=hours,
    )
    # Saturday 12:00 UTC → definitely closed
    saturday = datetime(2024, 1, 6, 12, 0)
    report = trader.run_once(now=saturday)

    assert report.actions == []
    assert not portfolio.positions


def test_auto_trader_run_loop_respects_max_cycles(ohlcv_uptrend):
    data = FakeDataFetcher(ohlcv_uptrend)
    predictor = StubPredictor(direction="neutral", confidence=0.0)
    risk = RiskManager(min_confidence=0.5)
    portfolio = Portfolio(initial_capital=10_000.0)
    broker = PaperBroker(portfolio, quote_fn=lambda t: 100.0)

    trader = AutoTrader(
        tickers=["AAPL"], predictor=predictor, risk=risk,
        broker=broker, portfolio=portfolio, data_fetcher=data,
    )
    sleep_calls: list[int] = []
    cycles = trader.run(
        interval_seconds=1, max_cycles=3,
        sleep_fn=lambda s: sleep_calls.append(s),
    )
    assert len(cycles) == 3
    # sleep between cycles only (no trailing sleep after the last cycle)
    assert sleep_calls == [1, 1]
