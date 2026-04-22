from src.backtest import Backtester
from src.prediction import SignalScorer, UnifiedPredictor
from src.trading import RiskManager


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
