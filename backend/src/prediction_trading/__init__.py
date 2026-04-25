"""prediction-trading: automated stock trading with AI-assisted signal generation."""

__version__ = "0.1.0"

from .system import PredictionTradingSystem
from .trading import AutoTrader, MarketHours, PaperBroker, StateStore

__all__ = [
    "PredictionTradingSystem",
    "AutoTrader",
    "PaperBroker",
    "StateStore",
    "MarketHours",
]
