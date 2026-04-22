"""Automated trading engine.

Ties every building block together to execute real (or simulated) trades
on a schedule:

    DataFetcher  →  UnifiedPredictor  →  RiskManager  →  Broker  →  Portfolio

Each *cycle* loops over the watchlist and does, per ticker:

1. Refresh OHLCV and compute indicators.
2. Check open positions for stop-loss / take-profit hits → close via broker.
3. Mark the portfolio to the latest quote.
4. Ask the predictor for a signal. If the :class:`RiskManager` approves,
   submit a market order to the broker.
5. Persist portfolio state + append to a CSV trade log.

The engine is broker-agnostic: plug in a :class:`PaperBroker` for
simulation, or a real-broker adapter that satisfies the
:class:`~src.trading.broker.BaseBroker` interface.
"""
from __future__ import annotations

import csv
import time
from dataclasses import dataclass, field
from datetime import datetime, time as dtime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from ..data_fetcher import DataFetcher, MarketData
from ..indicators import TechnicalIndicators
from ..logger import get_logger
from ..prediction import Prediction, UnifiedPredictor
from .broker import BaseBroker, Order
from .portfolio import Portfolio
from .risk_manager import RiskManager
from .state import StateStore


# =========================================================================
# Action / cycle reports
# =========================================================================
@dataclass
class TickerAction:
    ticker: str
    timestamp: datetime
    action: str                       # "open" | "close" | "hold" | "skip" | "error"
    reason: str = ""
    direction: str | None = None
    confidence: float | None = None
    price: float | None = None
    quantity: int | None = None
    pnl: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None

    def as_row(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "ticker": self.ticker,
            "action": self.action,
            "direction": self.direction or "",
            "confidence": f"{self.confidence:.4f}" if self.confidence is not None else "",
            "price": f"{self.price:.4f}" if self.price is not None else "",
            "quantity": self.quantity if self.quantity is not None else "",
            "stop_loss": f"{self.stop_loss:.4f}" if self.stop_loss is not None else "",
            "take_profit": f"{self.take_profit:.4f}" if self.take_profit is not None else "",
            "pnl": f"{self.pnl:.4f}" if self.pnl is not None else "",
            "reason": self.reason,
        }


@dataclass
class CycleReport:
    started_at: datetime
    finished_at: datetime
    actions: list[TickerAction] = field(default_factory=list)
    equity: float | None = None
    cash: float | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def opened(self) -> list[TickerAction]:
        return [a for a in self.actions if a.action == "open"]

    @property
    def closed(self) -> list[TickerAction]:
        return [a for a in self.actions if a.action == "close"]


# =========================================================================
# Market hours helper
# =========================================================================
@dataclass
class MarketHours:
    """Simple US equities regular-session gate (09:30–16:00 ET, Mon–Fri)."""

    tz: str = "America/New_York"
    open_: dtime = dtime(9, 30)
    close: dtime = dtime(16, 0)

    def is_open(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(tz=timezone.utc)
        local = now.astimezone(ZoneInfo(self.tz))
        if local.weekday() >= 5:  # Sat/Sun
            return False
        return self.open_ <= local.time() <= self.close


# =========================================================================
# Auto trader
# =========================================================================
class AutoTrader:
    """Run the prediction → risk → execution loop across a watchlist."""

    def __init__(
        self,
        tickers: Iterable[str],
        predictor: UnifiedPredictor,
        risk: RiskManager,
        broker: BaseBroker,
        portfolio: Portfolio,
        *,
        data_fetcher: DataFetcher | None = None,
        lookback_days: int = 365,
        state_store: StateStore | None = None,
        trade_log: str | Path | None = None,
        log_dir: str | Path | None = None,
        market_hours: MarketHours | None = None,
        include_fundamentals: bool = True,
        dry_run: bool = False,
    ) -> None:
        self.tickers = [t.upper().strip() for t in tickers]
        if not self.tickers:
            raise ValueError("AutoTrader requires at least one ticker.")
        self.predictor = predictor
        self.risk = risk
        self.broker = broker
        self.portfolio = portfolio
        self.data_fetcher = data_fetcher or DataFetcher()
        self.lookback_days = lookback_days
        self.state_store = state_store
        self.trade_log = Path(trade_log) if trade_log else None
        self.market_hours = market_hours
        self.include_fundamentals = include_fundamentals
        self.dry_run = dry_run
        self.log = get_logger("prediction_trading.auto_trader",
                              log_dir=log_dir)
        self._cycles: list[CycleReport] = []

    # ------------------------------------------------------------ public
    @property
    def cycles(self) -> list[CycleReport]:
        return list(self._cycles)

    def run_once(self, *, now: datetime | None = None) -> CycleReport:
        """Execute a single full cycle across every watchlist ticker."""
        started = now or datetime.utcnow()
        report = CycleReport(started_at=started, finished_at=started)

        if self.market_hours is not None and not self.market_hours.is_open(started):
            self.log.info("Market closed — skipping cycle at %s", started.isoformat())
            report.finished_at = datetime.utcnow()
            self._cycles.append(report)
            return report

        for ticker in self.tickers:
            try:
                report.actions.extend(self._process_ticker(ticker, started))
            except Exception as exc:  # pragma: no cover - defensive
                self.log.exception("Cycle failed for %s", ticker)
                report.errors.append(f"{ticker}: {exc}")
                report.actions.append(TickerAction(
                    ticker=ticker, timestamp=started,
                    action="error", reason=str(exc),
                ))

        prices = self._latest_prices()
        self.portfolio.mark(started, prices)
        report.equity = self.portfolio.equity(prices)
        report.cash = self.portfolio.cash
        report.finished_at = datetime.utcnow()

        self._persist(report)
        self._cycles.append(report)
        return report

    def run(
        self,
        *,
        interval_seconds: int = 300,
        max_cycles: int | None = None,
        sleep_fn=time.sleep,
    ) -> list[CycleReport]:
        """Loop :meth:`run_once` forever (or until ``max_cycles``)."""
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")
        count = 0
        self.log.info(
            "Starting AutoTrader: tickers=%s interval=%ds dry_run=%s",
            ",".join(self.tickers), interval_seconds, self.dry_run,
        )
        while True:
            count += 1
            report = self.run_once()
            self.log.info(
                "Cycle %d done | equity=%.2f cash=%.2f opens=%d closes=%d errors=%d",
                count,
                report.equity or 0.0, report.cash or 0.0,
                len(report.opened), len(report.closed), len(report.errors),
            )
            if max_cycles is not None and count >= max_cycles:
                break
            sleep_fn(interval_seconds)
        return self.cycles

    # ---------------------------------------------------------- per-ticker
    def _process_ticker(self, ticker: str, when: datetime) -> list[TickerAction]:
        actions: list[TickerAction] = []
        market = self._fetch_market(ticker)
        price = market.current_price

        # 1) exit management
        position = self.portfolio.positions.get(ticker)
        if position is not None:
            should_exit, exit_reason = position.should_exit(price)
            if should_exit:
                actions.append(self._close(ticker, price, when, exit_reason))
                position = None

        # 2) propose new entry
        if position is not None:
            actions.append(TickerAction(
                ticker=ticker, timestamp=when, action="hold",
                reason="position already open", price=price,
                quantity=position.quantity,
                direction=position.side,
            ))
            return actions

        df = TechnicalIndicators.compute_all(market.ohlcv)
        if df.empty or df["ATR"].dropna().empty:
            actions.append(TickerAction(
                ticker=ticker, timestamp=when, action="skip",
                reason="insufficient history for indicators", price=price,
            ))
            return actions

        weekly = self._to_weekly(market.ohlcv)
        weekly_df = TechnicalIndicators.compute_all(weekly) if weekly is not None else None

        prediction: Prediction = self.predictor.predict(
            ticker=ticker, df=df, current_price=price,
            weekly=weekly_df, fundamentals=market.fundamentals,
        )
        atr = float(df["ATR"].dropna().iloc[-1])
        proposal = self.risk.evaluate(
            prediction, portfolio=self.portfolio, atr=atr, timestamp=when,
        )
        if proposal is None:
            actions.append(TickerAction(
                ticker=ticker, timestamp=when, action="skip",
                direction=prediction.direction,
                confidence=prediction.confidence,
                price=price,
                reason="signal rejected by risk manager",
            ))
            return actions

        if self.dry_run:
            actions.append(TickerAction(
                ticker=ticker, timestamp=when, action="skip",
                direction=proposal.side,
                confidence=prediction.confidence,
                price=proposal.entry_price,
                quantity=proposal.quantity,
                stop_loss=proposal.stop_loss,
                take_profit=proposal.take_profit,
                reason=f"dry-run ({proposal.rationale})",
            ))
            return actions

        order = Order(
            ticker=proposal.ticker,
            side=proposal.side,  # type: ignore[arg-type]
            quantity=proposal.quantity,
            stop_loss=proposal.stop_loss,
            take_profit=proposal.take_profit,
            rationale=proposal.rationale,
        )
        fill = self.broker.place_order(order)
        if fill is None:
            actions.append(TickerAction(
                ticker=ticker, timestamp=when, action="skip",
                direction=proposal.side,
                confidence=prediction.confidence,
                price=price,
                reason="broker rejected order",
            ))
            return actions

        actions.append(TickerAction(
            ticker=ticker, timestamp=fill.filled_at, action="open",
            direction=proposal.side,
            confidence=prediction.confidence,
            price=fill.fill_price,
            quantity=proposal.quantity,
            stop_loss=proposal.stop_loss,
            take_profit=proposal.take_profit,
            reason=proposal.rationale,
        ))
        return actions

    # ------------------------------------------------------------ helpers
    def _close(self, ticker: str, price: float, when: datetime,
               reason: str) -> TickerAction:
        trade = self.broker.close_position(
            ticker, reason=reason, quote=price, when=when,
        )
        return TickerAction(
            ticker=ticker, timestamp=when, action="close",
            reason=reason, price=price,
            quantity=trade.quantity if trade else None,
            pnl=trade.pnl if trade else None,
            direction=trade.side if trade else None,
        )

    def _fetch_market(self, ticker: str) -> MarketData:
        return self.data_fetcher.fetch(
            ticker,
            lookback_days=self.lookback_days,
            include_fundamentals=self.include_fundamentals,
        )

    def _latest_prices(self) -> dict[str, float]:
        prices: dict[str, float] = {}
        for ticker in set(list(self.tickers) + list(self.portfolio.positions.keys())):
            try:
                prices[ticker] = self.broker.get_quote(ticker)
            except Exception:
                continue
        return prices

    def _persist(self, report: CycleReport) -> None:
        if self.state_store is not None:
            try:
                self.state_store.save(self.portfolio)
            except Exception:  # pragma: no cover
                self.log.exception("Failed to save state")
        if self.trade_log is not None:
            self._append_trade_log(report)

    def _append_trade_log(self, report: CycleReport) -> None:
        rows = [a.as_row() for a in report.actions
                if a.action in {"open", "close"}]
        if not rows:
            return
        self.trade_log.parent.mkdir(parents=True, exist_ok=True)
        write_header = not self.trade_log.exists()
        with self.trade_log.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            if write_header:
                writer.writeheader()
            for row in rows:
                writer.writerow(row)

    @staticmethod
    def _to_weekly(df: pd.DataFrame) -> pd.DataFrame | None:
        if df is None or df.empty:
            return None
        rules = {"Open": "first", "High": "max", "Low": "min",
                 "Close": "last", "Volume": "sum"}
        resampled = df.resample("W").agg(rules).dropna()
        return resampled if not resampled.empty else None
