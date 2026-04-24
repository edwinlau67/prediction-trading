"""Single-ticker backtester.

The loop walks a warm-up window + test window bar-by-bar. On each bar it:
  1. Marks existing positions to the close and closes any that hit
     stop / take-profit.
  2. Feeds the warmed-up history into the (optionally AI-fused) predictor.
  3. Asks the risk manager whether the resulting signal should become
     a trade, and opens it if so.

Results include the full equity curve plus trade log and summary stats.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from ..indicators import TechnicalIndicators
from ..prediction import UnifiedPredictor
from ..trading.portfolio import Portfolio, Position
from ..trading.risk_manager import RiskManager


@dataclass
class BacktestResult:
    ticker: str
    start: datetime
    end: datetime
    portfolio: Portfolio
    stats: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        p = self.portfolio
        trades = p.closed_trades
        wins = [t for t in trades if t.is_win]
        losses = [t for t in trades if not t.is_win]
        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0.0
        total_loss_abs = abs(sum(t.pnl for t in losses))
        return {
            "ticker": self.ticker,
            "period": f"{self.start.date()} -> {self.end.date()}",
            "initial_capital": p.initial_capital,
            "final_equity": p.equity_curve[-1][1] if p.equity_curve else p.initial_capital,
            "return_pct": round(p.return_pct, 2),
            "max_drawdown_pct": round(p.max_drawdown, 2),
            "trades": len(trades),
            "win_rate_pct": round(p.win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(abs(sum(t.pnl for t in wins)) / total_loss_abs, 2)
                             if total_loss_abs > 0 else None,
        }


class Backtester:
    def __init__(
        self,
        predictor: UnifiedPredictor,
        risk: RiskManager,
        *,
        warmup_bars: int = 200,
    ) -> None:
        self.predictor = predictor
        self.risk = risk
        self.warmup_bars = warmup_bars

    def run(self, ticker: str, ohlcv: pd.DataFrame, *,
            initial_capital: float = 10_000.0,
            commission_per_trade: float = 1.0) -> BacktestResult:
        if len(ohlcv) <= self.warmup_bars:
            raise ValueError(
                f"Need more than {self.warmup_bars} bars of history for backtest."
            )

        enriched = TechnicalIndicators.compute_all(ohlcv)
        enriched = enriched.dropna(subset=["ATR", "SMA50"])
        if enriched.empty:
            raise ValueError("Indicator warmup produced no usable bars.")

        portfolio = Portfolio(initial_capital=initial_capital,
                              commission_per_trade=commission_per_trade)
        start = enriched.index[0].to_pydatetime()
        end = enriched.index[-1].to_pydatetime()

        for i in range(1, len(enriched)):
            today = enriched.iloc[: i + 1]
            bar = today.iloc[-1]
            ts = today.index[-1].to_pydatetime()
            price = float(bar["Close"])
            prices = {ticker: price}

            # 1) exit checks
            pos = portfolio.positions.get(ticker)
            if pos is not None:
                should, reason = pos.should_exit(price)
                if should:
                    portfolio.close(ticker, price, ts, reason=reason)

            portfolio.mark(ts, prices)

            if ticker in portfolio.positions:
                continue  # already long/short, don't stack

            # 2) predict + propose
            prediction = self.predictor.predict(
                ticker=ticker,
                df=today,
                current_price=price,
            )
            proposal = self.risk.evaluate(
                prediction, portfolio=portfolio,
                atr=float(bar["ATR"]), timestamp=ts,
            )
            if proposal is None:
                continue

            try:
                portfolio.open(Position(
                    ticker=proposal.ticker,
                    side=proposal.side,  # type: ignore[arg-type]
                    quantity=proposal.quantity,
                    entry_price=proposal.entry_price,
                    entry_time=ts,
                    stop_loss=proposal.stop_loss,
                    take_profit=proposal.take_profit,
                ))
            except ValueError:
                continue

        # flush remaining open positions at final close
        final_ts = enriched.index[-1].to_pydatetime()
        final_price = float(enriched["Close"].iloc[-1])
        if ticker in portfolio.positions:
            portfolio.close(ticker, final_price, final_ts, reason="eod_flush")

        result = BacktestResult(
            ticker=ticker, start=start, end=end, portfolio=portfolio
        )
        result.stats = result.summary()
        return result
