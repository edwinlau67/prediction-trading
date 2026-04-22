"""Top-level orchestrator: PredictionTradingSystem.

Glues every module together behind a friendly API modelled after
``AutomatedTradingSystem`` but enhanced with the Claude-powered
AI predictor and a unified prediction layer.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from .backtest import Backtester, BacktestResult
from .data_fetcher import DataFetcher, MarketData
from .indicators import TechnicalIndicators
from .logger import get_logger
from .prediction import AIPredictor, Prediction, SignalScorer, UnifiedPredictor
from .reporting import ChartBuilder, ReportWriter
from .trading import Portfolio, RiskManager


DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "default.yaml"


@dataclass
class _Config:
    portfolio: dict[str, Any]
    risk: dict[str, Any]
    signals: dict[str, Any]
    indicators: dict[str, Any]
    ai: dict[str, Any]
    data: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path | None = None) -> "_Config":
        target = Path(path) if path else DEFAULT_CONFIG
        data = yaml.safe_load(target.read_text()) if target.exists() else {}
        return cls(
            portfolio=data.get("portfolio", {}),
            risk=data.get("risk", {}),
            signals=data.get("signals", {}),
            indicators=data.get("indicators", {}),
            ai=data.get("ai", {}),
            data=data.get("data", {}),
        )


class PredictionTradingSystem:
    """High-level façade for prediction, backtesting, and reporting."""

    def __init__(
        self,
        ticker: str,
        *,
        initial_capital: float | None = None,
        config_path: str | Path | None = None,
        enable_ai: bool | None = None,
        api_key: str | None = None,
        out_root: str | Path = "results",
    ) -> None:
        self.ticker = ticker.upper().strip()
        self.cfg = _Config.load(config_path)
        self.logger = get_logger()

        if initial_capital is not None:
            self.cfg.portfolio["initial_capital"] = initial_capital
        if enable_ai is not None:
            self.cfg.ai["enabled"] = enable_ai

        self.data_fetcher = DataFetcher(interval=self.cfg.data.get("interval", "1d"))

        categories = tuple(self.cfg.indicators.get("categories") or ())
        self.scorer = SignalScorer(
            categories=categories or None,
            weights=self.cfg.signals.get("weights"),
            multi_timeframe_bonus=int(self.cfg.signals.get("multi_timeframe_bonus", 2)),
        )

        self.ai_predictor: AIPredictor | None = None
        if self.cfg.ai.get("enabled"):
            key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            self.ai_predictor = AIPredictor(
                api_key=key,
                model=os.environ.get("CLAUDE_MODEL",
                                     self.cfg.ai.get("model", "claude-sonnet-4-6")),
                max_tokens=self.cfg.ai.get("max_tokens", 2000),
                data_fetcher=self.data_fetcher,
                categories=categories or None,
            )

        self.predictor = UnifiedPredictor(
            scorer=self.scorer,
            ai=self.ai_predictor,
            ai_enabled=bool(self.cfg.ai.get("enabled")) and self.ai_predictor is not None,
            ai_weight=self.cfg.signals.get("ai_weight", 0.5),
            min_confidence=self.cfg.signals.get("min_confidence", 0.55),
            timeframe=self.cfg.ai.get("timeframe", "1w"),
        )

        self.risk = RiskManager(
            max_positions=self.cfg.portfolio.get("max_positions", 5),
            max_position_size_pct=self.cfg.portfolio.get("max_position_size_pct", 0.05),
            max_daily_loss_pct=self.cfg.risk.get("max_daily_loss_pct", 0.02),
            min_risk_reward=self.cfg.risk.get("min_risk_reward", 1.5),
            stop_loss_atr_mult=self.cfg.risk.get("stop_loss_atr_mult", 2.0),
            take_profit_atr_mult=self.cfg.risk.get("take_profit_atr_mult", 3.0),
            min_confidence=self.cfg.signals.get("min_confidence", 0.55),
        )

        self.report_writer = ReportWriter(out_root=out_root)
        self.chart_builder = ChartBuilder()

        self._market: MarketData | None = None

    # ------------------------------------------------------------------ data
    def fetch(self, *, lookback_days: int | None = None,
              start: str | None = None, end: str | None = None) -> MarketData:
        if start and end:
            df = self.data_fetcher.fetch_history(self.ticker, start=start, end=end)
            fund = self.data_fetcher.fetch_fundamentals(self.ticker)
            self._market = MarketData(
                ticker=self.ticker, ohlcv=df,
                current_price=float(df["Close"].iloc[-1]),
                fundamentals=fund,
            )
        else:
            lb = lookback_days or self.cfg.data.get("lookback_days", 365)
            self._market = self.data_fetcher.fetch(self.ticker, lookback_days=lb)
        return self._market

    # ------------------------------------------------------------ prediction
    def predict(self, market: MarketData | None = None) -> Prediction:
        mkt = market or self._market or self.fetch()
        df = TechnicalIndicators.compute_all(mkt.ohlcv)
        weekly = self._to_weekly(mkt.ohlcv)
        weekly_df = TechnicalIndicators.compute_all(weekly) if weekly is not None else None
        return self.predictor.predict(
            ticker=mkt.ticker, df=df,
            current_price=mkt.current_price,
            weekly=weekly_df,
            fundamentals=mkt.fundamentals,
        )

    # -------------------------------------------------------------- backtest
    def backtest(self, start: str, end: str) -> BacktestResult:
        df = self.data_fetcher.fetch_history(self.ticker, start=start, end=end)
        bt = Backtester(self.predictor, self.risk)
        capital = self.cfg.portfolio.get("initial_capital", 10_000.0)
        commission = self.cfg.portfolio.get("commission_per_trade", 1.0)
        result = bt.run(self.ticker, df, initial_capital=capital,
                        commission_per_trade=commission)
        self.logger.info("Backtest done: %s", result.stats)
        self._market = MarketData(ticker=self.ticker, ohlcv=df,
                                  current_price=float(df["Close"].iloc[-1]))
        return result

    # ---------------------------------------------------------------- report
    def save_report(
        self,
        *,
        result: BacktestResult | None = None,
        prediction: Prediction | None = None,
    ) -> Path:
        out_dir = self.report_writer.new_run_dir(self.ticker)
        chart_paths: dict[str, Path] = {}
        if result is not None and self._market is not None:
            chart_paths = self.chart_builder.save_all(result, out_dir,
                                                      self._market.ohlcv)
        report = self.report_writer.write(
            out_dir,
            result=result,
            prediction=prediction,
            chart_paths=chart_paths,
            title=f"{self.ticker} — Prediction & Trading Report",
        )
        self.logger.info("Report written: %s", report)
        return out_dir

    # ----------------------------------------------------------- internals
    @staticmethod
    def _to_weekly(df: pd.DataFrame) -> pd.DataFrame | None:
        if df is None or df.empty:
            return None
        rules = {"Open": "first", "High": "max", "Low": "min",
                 "Close": "last", "Volume": "sum"}
        return df.resample("W").agg(rules).dropna()
