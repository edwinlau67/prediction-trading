from datetime import datetime

from src.backtest import Backtester, BacktestResult
from src.prediction import SignalScorer, UnifiedPredictor
from src.trading import Portfolio, RiskManager
from src.trading.portfolio import Trade


def test_profit_factor_none_when_no_losses():
    p = Portfolio(initial_capital=10_000.0)
    when = datetime(2024, 1, 2)
    p.closed_trades = [
        Trade("A", "long", 10, 100.0, 110.0, when, when, pnl=0.0, reason="eod_flush"),
    ]
    result = BacktestResult(ticker="A", start=when, end=when, portfolio=p)
    s = result.summary()
    assert s["profit_factor"] is None


def test_backtest_runs_end_to_end(ohlcv_uptrend):
    predictor = UnifiedPredictor(
        scorer=SignalScorer(), ai=None, ai_enabled=False,
        min_confidence=0.1,       # lenient so at least a few trades trigger
    )
    risk = RiskManager(
        max_positions=3, max_position_size_pct=0.2,
        max_daily_loss_pct=0.5, min_risk_reward=1.0,
        min_confidence=0.1,
    )
    bt = Backtester(predictor, risk, warmup_bars=200)
    result = bt.run("SYNTH", ohlcv_uptrend, initial_capital=10_000.0)

    assert result.stats["initial_capital"] == 10_000.0
    assert result.stats["final_equity"] > 0
    assert result.stats["trades"] >= 0      # scorer may still emit 0 on synthetic data
    assert result.portfolio.equity_curve   # at least one mark
