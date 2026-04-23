"""Broker abstraction used by the automated trading engine.

The engine speaks to ``BaseBroker`` only. Two concrete implementations
ship out of the box:

* :class:`PaperBroker` — simulated fills against the latest quote from a
  :class:`~src.data_fetcher.DataFetcher` (or a user-supplied quote
  source). Drives the in-memory :class:`~src.trading.portfolio.Portfolio`
  exactly like the backtester does.
* :class:`RecordingBroker` — test double that records every call in
  memory. Used by the unit tests and handy for dry-runs.

A real broker (Alpaca, IBKR, Binance, etc.) plugs in by implementing the
same four methods: ``get_quote``, ``place_order``, ``close_position``,
``sync``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Literal

from .portfolio import Portfolio, Position, Trade

Side = Literal["long", "short"]
OrderType = Literal["market", "limit"]


@dataclass
class Order:
    """Intent to open a position. Broker decides how/when to fill it."""

    ticker: str
    side: Side
    quantity: int
    order_type: OrderType = "market"
    limit_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    rationale: str = ""
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Fill:
    """Confirmation returned by the broker for an executed order."""

    order: Order
    fill_price: float
    filled_at: datetime
    commission: float = 0.0
    broker_order_id: str | None = None


# =========================================================================
# Base class
# =========================================================================
class BaseBroker(ABC):
    """Minimal interface the AutoTrader needs from any broker."""

    @abstractmethod
    def get_quote(self, ticker: str) -> float:
        """Return the latest tradable price for ``ticker``."""

    @abstractmethod
    def place_order(self, order: Order) -> Fill | None:
        """Submit ``order``. Return a :class:`Fill` on success, else ``None``."""

    @abstractmethod
    def close_position(
        self,
        ticker: str,
        *,
        reason: str = "manual",
        quote: float | None = None,
        when: datetime | None = None,
    ) -> Trade | None:
        """Close an open position. Returns the resulting :class:`Trade`."""

    def sync(self) -> None:  # pragma: no cover - hook for real brokers
        """Reconcile local state with the broker (no-op for paper trading)."""
        return None


# =========================================================================
# Paper broker
# =========================================================================
QuoteFn = Callable[[str], float]


class PaperBroker(BaseBroker):
    """Simulated broker backed by an in-memory :class:`Portfolio`.

    Fills happen immediately at the latest quote returned by
    ``quote_fn``. If no custom callable is supplied we fall back to a
    :class:`~src.data_fetcher.DataFetcher` lookup of the last close.
    """

    def __init__(
        self,
        portfolio: Portfolio,
        *,
        quote_fn: QuoteFn | None = None,
        slippage_bps: float = 0.0,
    ) -> None:
        self.portfolio = portfolio
        self._quote_fn = quote_fn or self._default_quote
        self.slippage_bps = max(0.0, slippage_bps)
        self._data_fetcher = None  # lazy — only when default_quote is used

    # ----------------------------------------------------------- interface
    def get_quote(self, ticker: str) -> float:
        return float(self._quote_fn(ticker))

    def place_order(self, order: Order) -> Fill | None:
        if order.quantity <= 0:
            return None
        if order.ticker in self.portfolio.positions:
            return None  # policy: one position per ticker

        quote = self.get_quote(order.ticker)
        fill_price = self._apply_slippage(order.side, quote)

        if order.order_type == "limit" and order.limit_price is not None:
            if order.side == "long" and fill_price > order.limit_price:
                return None
            if order.side == "short" and fill_price < order.limit_price:
                return None

        stop = order.stop_loss if order.stop_loss is not None else (
            fill_price * 0.98 if order.side == "long" else fill_price * 1.02
        )
        target = order.take_profit if order.take_profit is not None else (
            fill_price * 1.03 if order.side == "long" else fill_price * 0.97
        )
        now = datetime.now(timezone.utc)
        position = Position(
            ticker=order.ticker,
            side=order.side,
            quantity=order.quantity,
            entry_price=fill_price,
            entry_time=now,
            stop_loss=float(stop),
            take_profit=float(target),
        )
        try:
            self.portfolio.open(position)
        except ValueError:
            return None
        return Fill(
            order=order,
            fill_price=fill_price,
            filled_at=now,
            commission=self.portfolio.commission_per_trade,
            broker_order_id=f"paper-{int(now.timestamp() * 1000)}",
        )

    def close_position(
        self,
        ticker: str,
        *,
        reason: str = "manual",
        quote: float | None = None,
        when: datetime | None = None,
    ) -> Trade | None:
        if ticker not in self.portfolio.positions:
            return None
        price = float(quote if quote is not None else self.get_quote(ticker))
        ts = when or datetime.now(timezone.utc)
        return self.portfolio.close(ticker, price, ts, reason=reason)

    # ----------------------------------------------------------- internals
    def _apply_slippage(self, side: Side, quote: float) -> float:
        if self.slippage_bps <= 0:
            return quote
        adj = quote * self.slippage_bps / 10_000.0
        return quote + adj if side == "long" else quote - adj

    def _default_quote(self, ticker: str) -> float:
        # Lazy import to keep tests / offline use lightweight.
        if self._data_fetcher is None:
            from ..data_fetcher import DataFetcher
            self._data_fetcher = DataFetcher()
        df = self._data_fetcher.fetch_history(ticker, lookback_days=5)
        if df.empty:
            raise RuntimeError(f"No quote available for {ticker}")
        return float(df["Close"].iloc[-1])


# =========================================================================
# Recording broker (testing / dry-run)
# =========================================================================
class RecordingBroker(BaseBroker):
    """Test double: records every call, never touches a portfolio.

    ``quote_source`` maps ticker → price. Missing tickers raise so tests
    fail loudly on unexpected calls.
    """

    def __init__(self, quote_source: dict[str, float] | None = None) -> None:
        self.quotes: dict[str, float] = dict(quote_source or {})
        self.orders: list[Order] = []
        self.fills: list[Fill] = []
        self.closes: list[tuple[str, str]] = []

    def set_quote(self, ticker: str, price: float) -> None:
        self.quotes[ticker] = float(price)

    def get_quote(self, ticker: str) -> float:
        if ticker not in self.quotes:
            raise KeyError(f"No quote set for {ticker}")
        return self.quotes[ticker]

    def place_order(self, order: Order) -> Fill | None:
        self.orders.append(order)
        fill = Fill(
            order=order,
            fill_price=self.get_quote(order.ticker),
            filled_at=order.submitted_at,
            commission=0.0,
            broker_order_id=f"rec-{len(self.orders)}",
        )
        self.fills.append(fill)
        return fill

    def close_position(
        self,
        ticker: str,
        *,
        reason: str = "manual",
        quote: float | None = None,
        when: datetime | None = None,
    ) -> Trade | None:
        self.closes.append((ticker, reason))
        return None
