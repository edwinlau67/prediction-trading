"""JSON persistence for the automated trader.

Keeps a compact snapshot of the live :class:`~src.trading.portfolio.Portfolio`
on disk so the engine can be stopped and resumed without losing positions,
cash, trade history, or the equity curve.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .portfolio import Portfolio, Position, Trade


def _ts(value: datetime) -> str:
    return value.isoformat()


def _parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


class StateStore:
    """Read/write a portfolio snapshot as pretty JSON."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    # ------------------------------------------------------------ writing
    def save(self, portfolio: Portfolio) -> Path:
        payload: dict[str, Any] = {
            "saved_at": _ts(datetime.now(timezone.utc)),
            "initial_capital": portfolio.initial_capital,
            "cash": portfolio.cash,
            "commission_per_trade": portfolio.commission_per_trade,
            "positions": [
                {
                    "ticker": pos.ticker,
                    "side": pos.side,
                    "quantity": pos.quantity,
                    "entry_price": pos.entry_price,
                    "entry_time": _ts(pos.entry_time),
                    "stop_loss": pos.stop_loss,
                    "take_profit": pos.take_profit,
                }
                for pos in portfolio.positions.values()
            ],
            "closed_trades": [
                {
                    "ticker": t.ticker,
                    "side": t.side,
                    "quantity": t.quantity,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "entry_time": _ts(t.entry_time),
                    "exit_time": _ts(t.exit_time),
                    "pnl": t.pnl,
                    "reason": t.reason,
                }
                for t in portfolio.closed_trades
            ],
            "equity_curve": [
                [_ts(ts), float(eq)] for ts, eq in portfolio.equity_curve
            ],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.path

    # ------------------------------------------------------------ reading
    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> Portfolio:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        portfolio = Portfolio(
            initial_capital=float(data["initial_capital"]),
            cash=float(data["cash"]),
            commission_per_trade=float(data.get("commission_per_trade", 1.0)),
        )
        for raw in data.get("positions", []):
            pos = Position(
                ticker=raw["ticker"],
                side=raw["side"],
                quantity=int(raw["quantity"]),
                entry_price=float(raw["entry_price"]),
                entry_time=_parse_ts(raw["entry_time"]),
                stop_loss=float(raw["stop_loss"]),
                take_profit=float(raw["take_profit"]),
            )
            portfolio.positions[pos.ticker] = pos
        for raw in data.get("closed_trades", []):
            portfolio.closed_trades.append(Trade(
                ticker=raw["ticker"],
                side=raw["side"],
                quantity=int(raw["quantity"]),
                entry_price=float(raw["entry_price"]),
                exit_price=float(raw["exit_price"]),
                entry_time=_parse_ts(raw["entry_time"]),
                exit_time=_parse_ts(raw["exit_time"]),
                pnl=float(raw["pnl"]),
                reason=raw.get("reason", "manual"),
            ))
        portfolio.equity_curve = [
            (_parse_ts(row[0]), float(row[1]))
            for row in data.get("equity_curve", [])
        ]
        return portfolio

    def load_or_create(self, *, initial_capital: float,
                       commission_per_trade: float = 1.0) -> Portfolio:
        if self.exists():
            return self.load()
        return Portfolio(
            initial_capital=initial_capital,
            commission_per_trade=commission_per_trade,
        )
