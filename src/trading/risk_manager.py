"""Rule-based risk manager.

Enforces position sizing, per-trade risk/reward, daily loss cap, and
maximum concurrent positions. Produces ``TradeProposal`` objects the
backtester / live runner can act on.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..prediction.predictor import Prediction
from .portfolio import Portfolio


@dataclass
class TradeProposal:
    ticker: str
    side: str                 # "long" | "short"
    quantity: int
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_per_share: float
    risk_reward: float
    rationale: str


class RiskManager:
    def __init__(
        self,
        *,
        max_positions: int = 5,
        max_position_size_pct: float = 0.05,
        max_daily_loss_pct: float = 0.02,
        min_risk_reward: float = 1.5,
        stop_loss_atr_mult: float = 2.0,
        take_profit_atr_mult: float = 3.0,
        min_confidence: float = 0.40,
    ) -> None:
        self.max_positions = max_positions
        self.max_position_size_pct = max_position_size_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.min_risk_reward = min_risk_reward
        self.stop_loss_atr_mult = stop_loss_atr_mult
        self.take_profit_atr_mult = take_profit_atr_mult
        self.min_confidence = min_confidence
        self._day_start_equity: dict[str, float] = {}

    def evaluate(
        self,
        prediction: Prediction,
        *,
        portfolio: Portfolio,
        atr: float,
        timestamp: datetime,
    ) -> TradeProposal | None:
        """Return a TradeProposal if the prediction passes every gate."""
        if prediction.direction == "neutral":
            return None
        if prediction.confidence < self.min_confidence:
            return None
        if len(portfolio.positions) >= self.max_positions:
            return None
        if prediction.ticker in portfolio.positions:
            return None
        if self._daily_loss_tripped(portfolio, timestamp):
            return None
        if atr <= 0:
            return None

        price = prediction.current_price
        side = "long" if prediction.direction == "bullish" else "short"

        if side == "long":
            stop = price - self.stop_loss_atr_mult * atr
            target = price + self.take_profit_atr_mult * atr
        else:
            stop = price + self.stop_loss_atr_mult * atr
            target = price - self.take_profit_atr_mult * atr

        risk_per_share = abs(price - stop)
        reward_per_share = abs(target - price)
        if risk_per_share <= 0:
            return None
        rr = reward_per_share / risk_per_share
        if rr < self.min_risk_reward:
            return None

        equity = portfolio.equity_curve[-1][1] if portfolio.equity_curve \
            else portfolio.equity({})
        max_notional = equity * self.max_position_size_pct
        quantity = int(max_notional // price)
        if quantity <= 0:
            return None
        cost = quantity * price + portfolio.commission_per_trade
        if cost > portfolio.cash:
            quantity = int((portfolio.cash - portfolio.commission_per_trade) // price)
        if quantity <= 0:
            return None

        return TradeProposal(
            ticker=prediction.ticker,
            side=side,
            quantity=quantity,
            entry_price=price,
            stop_loss=float(stop),
            take_profit=float(target),
            risk_per_share=float(risk_per_share),
            risk_reward=float(rr),
            rationale=f"{prediction.direction} (conf={prediction.confidence:.0%}); "
                      f"R:R={rr:.2f}",
        )

    # --------------------------------------------------------------- helpers
    def _daily_loss_tripped(self, portfolio: Portfolio, when: datetime) -> bool:
        key = when.strftime("%Y-%m-%d")
        if key not in self._day_start_equity:
            start = portfolio.equity_curve[-1][1] if portfolio.equity_curve \
                else portfolio.equity({})
            self._day_start_equity[key] = start
        start = self._day_start_equity[key]
        current = portfolio.equity_curve[-1][1] if portfolio.equity_curve else start
        dd = (start - current) / start if start else 0.0
        return dd >= self.max_daily_loss_pct
