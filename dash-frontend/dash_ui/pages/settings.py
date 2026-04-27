"""Settings page — read/write config/default.yaml via /config/ API endpoints."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from dash_ui import api, theme

dash.register_page(__name__, path="/settings", name="Settings", order=8)

_ALL_CATEGORIES = ["trend", "momentum", "volatility", "volume", "support",
                   "fundamental", "news", "macro", "sector"]

_CLAUDE_MODELS = [
    {"label": "claude-sonnet-4-6", "value": "claude-sonnet-4-6"},
    {"label": "claude-opus-4-7", "value": "claude-opus-4-7"},
    {"label": "claude-haiku-4-5-20251001", "value": "claude-haiku-4-5-20251001"},
]

_TIMEFRAMES = [{"label": t, "value": t} for t in ["1d", "1w", "1m", "3m", "6m", "1y"]]
_DATA_SOURCES = [{"label": s, "value": s} for s in ["yfinance", "alpaca", "both"]]
_BROKER_TYPES = [{"label": b, "value": b} for b in ["paper", "alpaca"]]


def _label(text: str) -> dbc.Label:
    return dbc.Label(text, style={"color": theme.MUTED, "fontSize": "12px"})


layout = dbc.Container(
    [
        dcc.Interval(id="settings-load-trigger", interval=999_999_999, n_intervals=0, max_intervals=1),
        html.H4("Settings", className="mt-4 mb-3", style={"color": theme.TEXT}),
        html.Div(id="settings-api-banner"),
        html.Div(id="settings-save-msg"),

        dbc.Accordion([

            dbc.AccordionItem([
                dbc.Row([
                    dbc.Col([_label("Initial Capital ($)"),
                             dbc.Input(id="cfg-initial-capital", type="number", min=1000, step=1000)], md=6),
                    dbc.Col([_label("Max Concurrent Positions"),
                             dbc.Input(id="cfg-max-positions", type="number", min=1, max=50)], md=6),
                ], className="g-3 mb-3"),
                dbc.Row([
                    dbc.Col([_label("Max Position Size (% of equity)"),
                             dbc.Input(id="cfg-max-pos-pct", type="number", min=0.01, max=0.50, step=0.01)], md=6),
                    dbc.Col([_label("Commission per Trade ($)"),
                             dbc.Input(id="cfg-commission", type="number", min=0, step=0.5)], md=6),
                ], className="g-3"),
            ], title="Portfolio"),

            dbc.AccordionItem([
                dbc.Row([
                    dbc.Col([_label("Max Daily Loss %"),
                             dbc.Input(id="cfg-max-daily-loss", type="number", min=0.005, max=0.10, step=0.005)], md=6),
                    dbc.Col([_label("Min Risk:Reward Ratio"),
                             dbc.Input(id="cfg-min-rr", type="number", min=0.5, max=10.0, step=0.5)], md=6),
                ], className="g-3 mb-3"),
                dbc.Row([
                    dbc.Col([_label("Stop Loss ATR Multiplier"),
                             dbc.Input(id="cfg-stop-atr", type="number", min=0.5, max=10.0, step=0.5)], md=6),
                    dbc.Col([_label("Take Profit ATR Multiplier"),
                             dbc.Input(id="cfg-tp-atr", type="number", min=0.5, max=20.0, step=0.5)], md=6),
                ], className="g-3"),
            ], title="Risk Management"),

            dbc.AccordionItem([
                dbc.Row([
                    dbc.Col([_label("Min Confidence Threshold (0–1)"),
                             dbc.Input(id="cfg-min-confidence", type="number", min=0.0, max=1.0, step=0.05)], md=6),
                    dbc.Col([_label("AI Weight in Fused Score (0=rule-only, 1=AI-only)"),
                             dbc.Input(id="cfg-ai-weight", type="number", min=0.0, max=1.0, step=0.1)], md=6),
                ], className="g-3 mb-3"),
                dbc.Row([
                    dbc.Col([_label("Multi-Timeframe Confluence Bonus (points)"),
                             dbc.Input(id="cfg-mtf-bonus", type="number", min=0, max=10, step=1)], md=6),
                ], className="g-3"),
            ], title="Signal Settings"),

            dbc.AccordionItem([
                _label("Active Indicator Categories"),
                dcc.Dropdown(
                    id="cfg-categories",
                    options=[{"label": c, "value": c} for c in _ALL_CATEGORIES],
                    multi=True,
                    className="mt-1",
                ),
            ], title="Indicator Categories"),

            dbc.AccordionItem([
                dbc.Row([
                    dbc.Col([_label("Enable AI Predictor"),
                             dbc.Switch(id="cfg-ai-enabled", value=True)], md=4),
                    dbc.Col([_label("Claude Model"),
                             dcc.Dropdown(id="cfg-ai-model", options=_CLAUDE_MODELS,
                                          clearable=False)], md=4),
                    dbc.Col([_label("AI Prediction Timeframe"),
                             dcc.Dropdown(id="cfg-ai-timeframe", options=_TIMEFRAMES,
                                          clearable=False)], md=4),
                ], className="g-3 mb-3"),
                dbc.Row([
                    dbc.Col([_label("Max Response Tokens"),
                             dbc.Input(id="cfg-max-tokens", type="number", min=500, max=8000, step=500)], md=4),
                ], className="g-3"),
            ], title="AI / Claude Settings"),

            dbc.AccordionItem([
                dbc.Row([
                    dbc.Col([_label("Cycle Interval (seconds)"),
                             dbc.Input(id="cfg-interval", type="number", min=60, max=3600, step=60)], md=4),
                    dbc.Col([_label("Dry Run (paper signals only)"),
                             dbc.Switch(id="cfg-dry-run", value=True)], md=4),
                    dbc.Col([_label("Enforce Market Hours (9:30–16:00 ET)"),
                             dbc.Switch(id="cfg-market-hours", value=False)], md=4),
                ], className="g-3 mb-3"),
                dbc.Row([
                    dbc.Col([_label("Simulated Slippage (basis points)"),
                             dbc.Input(id="cfg-slippage", type="number", min=0, max=100, step=1)], md=4),
                ], className="g-3"),
            ], title="Auto-Trader"),

            dbc.AccordionItem([
                dbc.Row([
                    dbc.Col([_label("OHLCV Data Source"),
                             dcc.Dropdown(id="cfg-data-source", options=_DATA_SOURCES, clearable=False)], md=6),
                ], className="g-3"),
            ], title="Data Source"),

            dbc.AccordionItem([
                dbc.Row([
                    dbc.Col([_label("Broker"),
                             dcc.Dropdown(id="cfg-broker-type", options=_BROKER_TYPES, clearable=False)], md=6),
                    dbc.Col([_label("Paper Trading Mode"),
                             dbc.Switch(id="cfg-paper-trading", value=True)], md=6),
                ], className="g-3"),
            ], title="Broker"),

        ], start_collapsed=True, className="mb-4"),

        dbc.Button("Save Settings", id="settings-save-btn", color="success", n_clicks=0),
        html.Br(), html.Br(),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("cfg-initial-capital", "value"),
    Output("cfg-max-positions", "value"),
    Output("cfg-max-pos-pct", "value"),
    Output("cfg-commission", "value"),
    Output("cfg-max-daily-loss", "value"),
    Output("cfg-min-rr", "value"),
    Output("cfg-stop-atr", "value"),
    Output("cfg-tp-atr", "value"),
    Output("cfg-min-confidence", "value"),
    Output("cfg-ai-weight", "value"),
    Output("cfg-mtf-bonus", "value"),
    Output("cfg-categories", "value"),
    Output("cfg-ai-enabled", "value"),
    Output("cfg-ai-model", "value"),
    Output("cfg-ai-timeframe", "value"),
    Output("cfg-max-tokens", "value"),
    Output("cfg-interval", "value"),
    Output("cfg-dry-run", "value"),
    Output("cfg-market-hours", "value"),
    Output("cfg-slippage", "value"),
    Output("cfg-data-source", "value"),
    Output("cfg-broker-type", "value"),
    Output("cfg-paper-trading", "value"),
    Output("settings-api-banner", "children"),
    Input("settings-load-trigger", "n_intervals"),
)
def _load_settings(_n):
    try:
        cfg = api.get_config()
    except Exception as exc:
        empty = [None] * 23
        banner = dbc.Alert(
            [html.Strong("API Offline — "), f"Cannot load settings: {exc}"],
            color="danger", className="mb-3",
        )
        return (*empty, banner)

    p = cfg.get("portfolio", {})
    r = cfg.get("risk", {})
    s = cfg.get("signals", {})
    ind = cfg.get("indicators", {})
    ai = cfg.get("ai", {})
    trader = cfg.get("trader", {})
    data = cfg.get("data", {})
    broker = cfg.get("broker", {})

    return (
        p.get("initial_capital", 10000),
        p.get("max_positions", 5),
        p.get("max_position_size_pct", 0.05),
        p.get("commission_per_trade", 1.0),
        r.get("max_daily_loss_pct", 0.02),
        r.get("min_risk_reward", 1.5),
        r.get("stop_loss_atr_mult", 2.0),
        r.get("take_profit_atr_mult", 3.0),
        s.get("min_confidence", 0.4),
        s.get("ai_weight", 0.5),
        s.get("multi_timeframe_bonus", 2),
        ind.get("categories", _ALL_CATEGORIES),
        ai.get("enabled", True),
        ai.get("model", "claude-sonnet-4-6"),
        ai.get("timeframe", "1w"),
        ai.get("max_tokens", 2000),
        trader.get("interval_seconds", 300),
        trader.get("dry_run", False),
        trader.get("enforce_market_hours", False),
        trader.get("slippage_bps", 5.0),
        data.get("source", "yfinance"),
        broker.get("type", "paper"),
        broker.get("paper_trading", True),
        html.Div(),
    )


@callback(
    Output("settings-save-msg", "children"),
    Input("settings-save-btn", "n_clicks"),
    State("cfg-initial-capital", "value"),
    State("cfg-max-positions", "value"),
    State("cfg-max-pos-pct", "value"),
    State("cfg-commission", "value"),
    State("cfg-max-daily-loss", "value"),
    State("cfg-min-rr", "value"),
    State("cfg-stop-atr", "value"),
    State("cfg-tp-atr", "value"),
    State("cfg-min-confidence", "value"),
    State("cfg-ai-weight", "value"),
    State("cfg-mtf-bonus", "value"),
    State("cfg-categories", "value"),
    State("cfg-ai-enabled", "value"),
    State("cfg-ai-model", "value"),
    State("cfg-ai-timeframe", "value"),
    State("cfg-max-tokens", "value"),
    State("cfg-interval", "value"),
    State("cfg-dry-run", "value"),
    State("cfg-market-hours", "value"),
    State("cfg-slippage", "value"),
    State("cfg-data-source", "value"),
    State("cfg-broker-type", "value"),
    State("cfg-paper-trading", "value"),
    prevent_initial_call=True,
)
def _save_settings(
    n_clicks,
    initial_capital, max_positions, max_pos_pct, commission,
    max_daily_loss, min_rr, stop_atr, tp_atr,
    min_confidence, ai_weight, mtf_bonus, categories,
    ai_enabled, ai_model, ai_timeframe, max_tokens,
    interval, dry_run, market_hours, slippage,
    data_source, broker_type, paper_trading,
):
    cfg = {
        "portfolio": {
            "initial_capital": float(initial_capital or 10000),
            "max_positions": int(max_positions or 5),
            "max_position_size_pct": float(max_pos_pct or 0.05),
            "commission_per_trade": float(commission or 1.0),
        },
        "risk": {
            "max_daily_loss_pct": float(max_daily_loss or 0.02),
            "min_risk_reward": float(min_rr or 1.5),
            "stop_loss_atr_mult": float(stop_atr or 2.0),
            "take_profit_atr_mult": float(tp_atr or 3.0),
        },
        "signals": {
            "min_confidence": float(min_confidence or 0.4),
            "ai_weight": float(ai_weight or 0.5),
            "multi_timeframe_bonus": int(mtf_bonus or 2),
        },
        "indicators": {
            "categories": list(categories or _ALL_CATEGORIES),
        },
        "ai": {
            "enabled": bool(ai_enabled),
            "model": ai_model or "claude-sonnet-4-6",
            "timeframe": ai_timeframe or "1w",
            "max_tokens": int(max_tokens or 2000),
        },
        "trader": {
            "interval_seconds": int(interval or 300),
            "dry_run": bool(dry_run),
            "enforce_market_hours": bool(market_hours),
            "slippage_bps": float(slippage or 5.0),
        },
        "data": {
            "source": data_source or "yfinance",
        },
        "broker": {
            "type": broker_type or "paper",
            "paper_trading": bool(paper_trading),
        },
    }

    try:
        api.put_config(cfg)
        return dbc.Alert(
            "Settings saved. Restart the API server to apply changes.",
            color="success", duration=5000,
        )
    except Exception as exc:
        return dbc.Alert(f"Failed to save: {exc}", color="danger")
