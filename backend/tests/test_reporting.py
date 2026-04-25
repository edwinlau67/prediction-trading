"""Tests for reporting modules (no chart rendering, no network)."""
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from prediction_trading.reporting.report import ReportWriter


def _minimal_prediction(ticker: str = "AAPL", direction: str = "bullish"):
    from prediction_trading.prediction.predictor import Prediction
    from prediction_trading.prediction.factor import Factor
    return Prediction(
        ticker=ticker, direction=direction, confidence=0.7,
        current_price=175.0, price_target=185.0,
        target_date="2026-05-01", risk_level="medium",
        factors=[
            Factor("trend", "SMA50 uptrend", "bullish", 1, "price above SMA50"),
        ],
    )


def _minimal_backtest_result(ticker: str = "AAPL"):
    from prediction_trading.backtest.backtester import BacktestResult
    from prediction_trading.trading.portfolio import Portfolio
    portfolio = Portfolio(initial_capital=10_000.0)
    result = BacktestResult(
        ticker=ticker,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 12, 31),
        portfolio=portfolio,
    )
    result.stats = result.summary()
    return result


class TestReportWriter:
    def test_write_creates_report_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            writer = ReportWriter(out_root=tmp)
            prediction = _minimal_prediction()
            report_path = writer.write(out_dir, prediction=prediction)
            assert report_path.exists(), f"Expected report at {report_path}"
            assert report_path.name == "report.md"

    def test_report_contains_ticker_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            writer = ReportWriter(out_root=tmp)
            prediction = _minimal_prediction("TSLA")
            report_path = writer.write(out_dir, prediction=prediction)
            content = report_path.read_text()
            assert "TSLA" in content

    def test_report_contains_direction(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            writer = ReportWriter(out_root=tmp)
            prediction = _minimal_prediction(direction="bearish")
            report_path = writer.write(out_dir, prediction=prediction)
            content = report_path.read_text()
            assert "BEARISH" in content or "bearish" in content

    def test_report_contains_backtest_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            writer = ReportWriter(out_root=tmp)
            result = _minimal_backtest_result("MSFT")
            report_path = writer.write(out_dir, result=result)
            content = report_path.read_text()
            assert "MSFT" in content or "Backtest" in content

    def test_new_run_dir_has_timestamp_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = ReportWriter(out_root=tmp)
            run_dir = writer.new_run_dir("AAPL")
            assert run_dir.exists()
            assert "AAPL" in str(run_dir) or "backtest" in str(run_dir).lower()

    def test_write_both_prediction_and_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            writer = ReportWriter(out_root=tmp)
            prediction = _minimal_prediction()
            result = _minimal_backtest_result()
            report_path = writer.write(out_dir, prediction=prediction, result=result)
            content = report_path.read_text()
            assert "AAPL" in content
            assert len(content) > 100


class TestPredictionReportWriter:
    def test_write_predictions_md(self):
        from prediction_trading.reporting.prediction_report import PredictionReportEntry, PredictionReportWriter

        rng = np.random.default_rng(1)
        close = 100.0 * np.exp(np.cumsum(rng.normal(0.001, 0.01, 50)))
        idx = pd.bdate_range("2024-01-01", periods=50)
        ohlcv = pd.DataFrame({
            "Open": close, "High": close * 1.01,
            "Low": close * 0.99, "Close": close, "Volume": 1e6,
        }, index=idx)

        pred = _minimal_prediction()

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            writer = PredictionReportWriter(out_root=tmp)
            entries = [PredictionReportEntry(
                prediction=pred, timeframe="1w",
                chart_path=Path(tmp) / "chart.png",
                ohlcv=ohlcv,
            )]
            report_path = writer.write(run_dir, entries)
            assert report_path.exists(), f"Expected predictions.md at {report_path}"
            content = report_path.read_text()
            assert "AAPL" in content

    def test_run_dir_prefix_is_predict(self):
        from prediction_trading.reporting.prediction_report import PredictionReportWriter
        with tempfile.TemporaryDirectory() as tmp:
            writer = PredictionReportWriter(out_root=tmp)
            run_dir = writer.new_run_dir()
            assert run_dir.exists()
            assert "predict" in str(run_dir).lower()
