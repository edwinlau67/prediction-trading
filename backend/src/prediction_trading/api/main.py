"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .routers import backtest, config, portfolio, predict, scan, trading


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .deps import get_default_config
    get_default_config()
    yield


app = FastAPI(
    title="Prediction Trading API",
    version="0.1.0",
    description="REST API for the stock prediction and automated trading system.",
    lifespan=lifespan,
)

app.include_router(predict.router)
app.include_router(scan.router)
app.include_router(backtest.router)
app.include_router(trading.router)
app.include_router(portfolio.router)
app.include_router(config.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
