from datetime import datetime, timedelta

from src.trading.portfolio import Portfolio, Position


def _pos(ticker: str, price: float, qty: int, when: datetime) -> Position:
    return Position(
        ticker=ticker, side="long", quantity=qty,
        entry_price=price, entry_time=when,
        stop_loss=price * 0.95, take_profit=price * 1.1,
    )


def test_open_and_close_long_profit():
    when = datetime(2024, 1, 2)
    p = Portfolio(initial_capital=10_000.0, commission_per_trade=1.0)
    p.open(_pos("AAPL", 100.0, 10, when))
    assert p.cash == 10_000.0 - 100 * 10 - 1.0
    trade = p.close("AAPL", 110.0, when + timedelta(days=5), reason="take_profit")
    assert trade.pnl == 10 * (110 - 100) - 2 * 1.0
    assert p.cash == 10_000.0 + trade.pnl
    assert len(p.closed_trades) == 1


def test_insufficient_cash_raises():
    when = datetime(2024, 1, 2)
    p = Portfolio(initial_capital=500.0, commission_per_trade=1.0)
    try:
        p.open(_pos("AAPL", 100.0, 10, when))
    except ValueError:
        return
    raise AssertionError("Expected ValueError for insufficient cash.")


def test_equity_tracks_position_value():
    when = datetime(2024, 1, 2)
    p = Portfolio(initial_capital=5_000.0, commission_per_trade=1.0)
    p.open(_pos("AAPL", 100.0, 5, when))
    assert p.equity({"AAPL": 100.0}) == 5_000.0 - 1.0       # only commission
    assert p.equity({"AAPL": 110.0}) == 5_000.0 - 1.0 + 50


def test_drawdown_calculation():
    when = datetime(2024, 1, 2)
    p = Portfolio(initial_capital=10_000.0)
    curve = [
        (when + timedelta(days=i), v)
        for i, v in enumerate([10_000, 10_500, 9_500, 9_800, 11_000])
    ]
    p.equity_curve = curve
    assert round(p.max_drawdown, 2) == round((10500 - 9500) / 10500 * 100, 2)
