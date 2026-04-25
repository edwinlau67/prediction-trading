"""FastAPI dependency injection — shared singletons."""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_default_config():
    from prediction_trading.system import _Config
    return _Config.load()
