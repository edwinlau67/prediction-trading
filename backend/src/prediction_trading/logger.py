"""Centralised logging setup."""
from __future__ import annotations

import logging
import sys
from pathlib import Path


_DEFAULT_FMT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
_configured = False


def get_logger(name: str = "prediction_trading", *, level: int = logging.INFO,
               log_dir: str | Path | None = None) -> logging.Logger:
    """Return a configured logger. Safe to call repeatedly."""
    global _configured
    logger = logging.getLogger(name)
    if _configured:
        return logger

    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(_DEFAULT_FMT, datefmt="%Y-%m-%d %H:%M:%S")

    stream = logging.StreamHandler(stream=sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    if log_dir is not None:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path / "prediction_trading.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    _configured = True
    return logger
