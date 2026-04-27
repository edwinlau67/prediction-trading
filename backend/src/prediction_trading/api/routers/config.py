"""GET /config/, PUT /config/ — read and write config/default.yaml."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/config", tags=["config"])

_CONFIG_PATH = Path(__file__).parents[5] / "config" / "default.yaml"
_ALLOWED_KEYS = {"portfolio", "risk", "signals", "indicators", "ai", "trader", "data", "broker"}


def _load() -> dict[str, Any]:
    return yaml.safe_load(_CONFIG_PATH.read_text()) or {}


@router.get("/")
def get_config() -> dict[str, Any]:
    try:
        return _load()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/")
def put_config(body: dict[str, Any]) -> dict[str, Any]:
    try:
        existing = _load()
        for key, value in body.items():
            if key in _ALLOWED_KEYS:
                existing[key] = value
        _CONFIG_PATH.write_text(
            yaml.dump(existing, default_flow_style=False, sort_keys=False)
        )
        return existing
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
