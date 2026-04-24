"""Portfolio, position, and trade primitives for the backtester and live runner."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Side = Literal["long", "short"]


@dataclass
class Position:
    ticker: str
    side: Side
    quantity: int
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float

    def unrealised(self, price: float) -> float:
        sign = 1.0 if self.side == "long" else -1.0
        return sign * (price - self.entry_price) * self.quantity

    def should_exit(self, price: float) -> tuple[bool, str]:
        if self.side == "long":
            if price <= self.stop_loss:
                return True, "stop_loss"
            if price >= self.take_profit:
                return True, "take_profit"
        else:
            if price >= self.stop_loss:
                return True, "stop_loss"
            if price <= self.take_profit:
                return True, "take_profit"
        return False, ""


@dataclass
class Trade:
    ticker: str
    side: Side
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    reason: str

    @property
    def return_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        sign = 1.0 if self.side == "long" else -1.0
        return sign * (self.exit_price - self.entry_price) / self.entry_price

    @property
    def is_win(self) -> bool:
        return self.pnl > 0


@dataclass
class Portfolio:
    initial_capital: float = 10_000.0
    cash: float = 0.0
    commission_per_trade: float = 1.0
    positions: dict[str, Position] = field(default_factory=dict)
    closed_trades: list[Trade] = field(default_factory=list)
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.cash:
            self.cash = self.initial_capital

    # ------------------------------------------------------------------ api
    def equity(self, prices: dict[str, float]) -> float:
        value = self.cash
        for ticker, pos in self.positions.items():
            px = prices.get(ticker, pos.entry_price)
            value += pos.unrealised(px) + pos.entry_price * pos.quantity
        return value

    def mark(self, timestamp: datetime, prices: dict[str, float]) -> None:
        self.equity_curve.append((timestamp, self.equity(prices)))

    def open(self, position: Position) -> None:
        cost = position.quantity * position.entry_price + self.commission_per_trade
        if cost > self.cash:
            raise ValueError(
                f"Insufficient cash (${self.cash:.2f}) to open {position.ticker}"
            )
        self.cash -= cost
        self.positions[position.ticker] = position

    def close(self, ticker: str, price: float, when: datetime, reason: str = "manual"
              ) -> Trade:
        if ticker not in self.positions:
            raise KeyError(f"No open position in {ticker}")
        pos = self.positions.pop(ticker)
        if pos.side == "long":
            proceeds = pos.quantity * price - self.commission_per_trade
        else:
            # Margin model: open() deducted entry_price*qty as collateral.
            # On close, return collateral + unrealised P&L, minus commission.
            proceeds = (2 * pos.entry_price - price) * pos.quantity - self.commission_per_trade
        self.cash += proceeds
        pnl = pos.unrealised(price) - (2 * self.commission_per_trade)
        trade = Trade(
            ticker=ticker,
            side=pos.side,
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            exit_price=price,
            entry_time=pos.entry_time,
            exit_time=when,
            pnl=pnl,
            reason=reason,
        )
        self.closed_trades.append(trade)
        return trade

    # ------------------------------------------------------------------ stats
    @property
    def return_pct(self) -> float:
        if not self.equity_curve:
            return 0.0
        final = self.equity_curve[-1][1]
        return (final - self.initial_capital) / self.initial_capital * 100.0

    @property
    def win_rate(self) -> float:
        if not self.closed_trades:
            return 0.0
        wins = sum(1 for t in self.closed_trades if t.is_win)
        return wins / len(self.closed_trades) * 100.0

    @property
    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.initial_capital
        worst = 0.0
        for _, eq in self.equity_curve:
            peak = max(peak, eq)
            dd = (peak - eq) / peak if peak else 0.0
            worst = max(worst, dd)
        return worst * 100.0
