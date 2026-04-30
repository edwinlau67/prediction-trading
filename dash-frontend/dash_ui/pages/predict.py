"""Prediction page — user-triggered via button, results stored cross-page."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html, no_update

from dash_ui import api, components, theme

dash.register_page(__name__, path="/predict", name="Predict", order=1)

_ALL_CATEGORIES = ["trend", "momentum", "volatility", "volume", "support", "fundamental", "news", "macro", "sector"]
_TIMEFRAMES = ["1d", "1w", "1m", "3m", "6m", "1y", "2y", "5y"]
_CLAUDE_MODELS = [
    {"label": "claude-sonnet-4-6", "value": "claude-sonnet-4-6"},
    {"label": "claude-opus-4-7", "value": "claude-opus-4-7"},
    {"label": "claude-haiku-4-5-20251001", "value": "claude-haiku-4-5-20251001"},
]

_TIMING_COLORS = {
    "BUY_NOW": theme.GREEN, "BUY_ON_DIP": theme.BLUE, "BUY_ON_BREAKOUT": theme.BLUE,
    "SELL_NOW": theme.RED, "SELL_TRAILING": theme.YELLOW,
    "HOLD": theme.MUTED, "WAIT": theme.MUTED,
}

layout = dbc.Container(
    [
        html.H4("Stock Prediction", className="mt-4 mb-3", style={"color": theme.TEXT}),

        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ticker Symbol", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="pred-ticker", placeholder="e.g. AAPL", type="text",
                              debounce=False, style={"textTransform": "uppercase"}),
                ], md=2),
                dbc.Col([
                    dbc.Label("Timeframe", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Dropdown(
                        id="pred-timeframe",
                        options=[{"label": t, "value": t} for t in _TIMEFRAMES],
                        value="1w", clearable=False,
                    ),
                ], md=2),
                dbc.Col([
                    dbc.Label("Enable AI (Claude)", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Switch(id="pred-ai-toggle", value=False, label="AI Analysis"),
                ], md=2),
                dbc.Col([
                    dbc.Label("Claude Model", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Dropdown(id="pred-ai-model", options=_CLAUDE_MODELS,
                                 value="claude-sonnet-4-6", clearable=False),
                ], md=3),
                dbc.Col([
                    dbc.Label("4H Confluence", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Switch(id="pred-4h-toggle", value=False, label="Enable 4H"),
                ], md=1),
                dbc.Col([
                    dbc.Label("Save Report", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Switch(id="pred-save-report", value=False, label="results/"),
                ], md=1),
                dbc.Col([
                    dbc.Label("Run", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Button("Run Prediction", id="pred-run-btn", color="success", n_clicks=0),
                ], md=1),
            ], className="g-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Indicator Categories", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Dropdown(
                        id="pred-categories",
                        options=[{"label": c.title(), "value": c} for c in _ALL_CATEGORIES],
                        value=_ALL_CATEGORIES, multi=True,
                    ),
                ], md=12),
            ], className="g-3 mt-1"),
        ]), className="mb-4"),

        html.Div(id="pred-error"),
        html.Div(id="pred-save-status"),
        html.Div(id="pred-summary-save-status"),
        dcc.Loading(id="pred-loading", type="default", children=html.Div(id="pred-results")),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("predict-result-store", "data"),
    Output("pred-error", "children"),
    Output("pred-results", "children"),
    Output("pred-save-status", "children"),
    Input("pred-run-btn", "n_clicks"),
    State("pred-ticker", "value"),
    State("pred-timeframe", "value"),
    State("pred-ai-toggle", "value"),
    State("pred-4h-toggle", "value"),
    State("pred-categories", "value"),
    State("pred-ai-model", "value"),
    State("pred-save-report", "value"),
    prevent_initial_call=True,
)
def _run_prediction(n_clicks, ticker, timeframe, enable_ai, use_4h, categories, ai_model, save_report):
    if not ticker:
        return no_update, dbc.Alert("Please enter a ticker symbol.", color="warning"), no_update, no_update

    ticker = ticker.strip().upper()
    try:
        result = api.predict(
            ticker, timeframe, enable_ai, categories or None,
            use_4h=use_4h, save_report=bool(save_report),
        )
    except Exception as exc:
        err = dbc.Alert([html.Strong("Prediction failed: "), str(exc)], color="danger")
        return no_update, err, no_update, no_update

    # Fetch macro context for market index table (non-blocking)
    try:
        macro = api.predict_macro()
        result["macro"] = macro
    except Exception:
        result["macro"] = {}

    results_ui = _build_results(result)

    save_status: object = None
    report_path = result.get("report_path")
    if save_report and report_path:
        save_status = dbc.Alert(
            [html.Strong("Report saved: "), html.Code(report_path)],
            color="success", dismissable=True, className="mt-2 mb-2",
        )
    elif save_report and not report_path:
        save_status = dbc.Alert(
            "Save report was requested but the server could not write the file.",
            color="warning", dismissable=True, className="mt-2 mb-2",
        )

    return result, None, results_ui, save_status


@callback(
    Output("pred-summary-save-status", "children"),
    Input("pred-summary-save-btn", "n_clicks"),
    State("predict-result-store", "data"),
    State("pred-timeframe", "value"),
    State("pred-ai-toggle", "value"),
    State("pred-4h-toggle", "value"),
    State("pred-categories", "value"),
    prevent_initial_call=True,
)
def _save_summary(n_clicks, result, timeframe, enable_ai, use_4h, categories):
    if not n_clicks or not result:
        return no_update
    ticker = result.get("ticker", "")
    if not ticker:
        return no_update
    try:
        resp = api.predict(
            ticker, timeframe or "1w", bool(enable_ai),
            categories or None, use_4h=bool(use_4h), save_report=True,
        )
    except Exception as exc:
        return dbc.Alert(
            [html.Strong("Could not save report: "), str(exc)],
            color="danger", dismissable=True, className="mt-2 mb-2",
        )
    path = resp.get("report_path")
    if not path:
        return dbc.Alert(
            "Server could not write the report.",
            color="warning", dismissable=True, className="mt-2 mb-2",
        )
    return dbc.Alert(
        [html.Strong("Report saved: "), html.Code(path),
         html.Span(" (predictions.md + chart)", className="ms-2 text-muted")],
        color="success", dismissable=True, className="mt-2 mb-2",
    )


def _build_results(result: dict) -> object:
    direction = result.get("direction", "neutral")
    confidence = result.get("confidence", 0.0)
    ticker = result.get("ticker", "")
    price = result.get("current_price", 0.0)
    target = result.get("price_target")
    risk = result.get("risk_level", "medium")
    factors = result.get("factors", [])
    meta = result.get("meta", {})
    narrative = meta.get("ai_narrative") or meta.get("narrative")
    timing = result.get("timing")
    ohlcv = result.get("ohlcv", [])
    macro = result.get("macro", {})

    price_change_pct = None
    if target and price:
        price_change_pct = (target - price) / price * 100

    # Build signal tab content
    signal_content = [
        dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H5(ticker, style={"color": theme.TEXT, "marginBottom": "12px"}),
                    html.Div(components.direction_badge(direction), className="mb-3"),
                    html.Div([
                        html.Span("Confidence: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                        html.Span(f"{confidence * 100:.1f}%",
                                  style={"color": theme.TEXT, "fontWeight": "600"}),
                    ], className="mb-2"),
                    html.Div([
                        html.Span("Current Price: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                        html.Span(f"${price:.2f}", style={"color": theme.TEXT, "fontWeight": "600"}),
                    ], className="mb-2"),
                    *([html.Div([
                        html.Span("Price Target: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                        html.Span(
                            f"${target:.2f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.1f}%)",
                            style={"color": theme.GREEN if price_change_pct >= 0 else theme.RED,
                                   "fontWeight": "600"},
                        ),
                    ], className="mb-2")] if target and price_change_pct is not None else []),
                    html.Div([
                        html.Span("Risk Level: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                        html.Span(risk.title(), style={"color": theme.YELLOW, "fontWeight": "600"}),
                    ], className="mb-2"),
                ]), className="h-100"),
            ], md=4),
            dbc.Col([
                dcc.Graph(figure=components.confidence_gauge(direction, confidence),
                          config={"displayModeBar": False}),
            ], md=8),
        ], className="g-3"),
    ]

    # Timing Recommendation card
    if timing:
        signal_content.append(_build_timing_card(timing))

    indicators = result.get("indicators") or {}
    levels = result.get("levels") or {}
    fundamentals = result.get("fundamentals") or {}
    indexes = macro.get("indexes", [])

    # Market Index Overview table (Signal tab)
    if indexes:
        signal_content.append(_build_index_table(indexes))

    factors_tab = dcc.Graph(
        figure=components.factor_bar_chart(factors),
        config={"displayModeBar": False},
    )

    summary_md = _build_summary_markdown(result)
    summary_tab = html.Div([
        dcc.Loading(
            dbc.Button(
                "Save Report (with charts) to results/",
                id="pred-summary-save-btn",
                color="secondary", size="sm", className="mb-3",
            ),
            type="circle",
        ),
        dbc.Card(dbc.CardBody(
            dcc.Markdown(
                summary_md,
                style={"color": theme.TEXT, "fontSize": "13px"},
                link_target="_blank",
            ),
        )),
    ], className="mt-3")

    tabs = [
        dbc.Tab(html.Div(signal_content), label="Signal", tab_id="sig"),
        dbc.Tab(summary_tab, label="Summary", tab_id="summary"),
        dbc.Tab(factors_tab, label=f"Factors ({len(factors)})", tab_id="fac"),
    ]

    if ohlcv:
        entry = timing.get("entry_price") if timing else None
        stop_loss = timing.get("stop_loss") if timing else None
        tp = timing.get("take_profit") if timing else None
        timing_for_chart = {"entry_price": entry, "stop_loss": stop_loss, "take_profit": tp} if timing else None
        analysis_fig = components.analysis_chart(ohlcv, indicators, levels, timing=timing_for_chart)
        tabs.append(dbc.Tab(
            dcc.Graph(
                figure=analysis_fig,
                config={"displayModeBar": True, "scrollZoom": True, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
                style={"height": "1200px"},
            ),
            label="Analysis", tab_id="analysis",
        ))

    if fundamentals:
        tabs.append(dbc.Tab(
            dcc.Graph(
                figure=components.fundamentals_chart(fundamentals, ticker),
                config={"displayModeBar": False},
            ),
            label="Fundamentals", tab_id="fund",
        ))

    if indexes:
        tabs.append(dbc.Tab(
            dcc.Graph(
                figure=components.index_performance_chart(indexes),
                config={"displayModeBar": False},
            ),
            label="Market", tab_id="market",
        ))

    if narrative:
        tabs.append(dbc.Tab(
            dbc.Card(dbc.CardBody(html.Pre(
                narrative,
                style={"color": theme.TEXT, "fontSize": "13px", "whiteSpace": "pre-wrap", "margin": 0},
            ))),
            label="AI Narrative", tab_id="ai",
        ))

    return dbc.Tabs(tabs, active_tab="sig", className="mt-2")


def _build_timing_card(timing: dict) -> dbc.Card:
    action = timing.get("action", "WAIT")
    reason = timing.get("reason", "")
    entry = timing.get("entry_price")
    stop = timing.get("stop_loss")
    tp = timing.get("take_profit")
    color = _TIMING_COLORS.get(action, theme.MUTED)

    kpis = []
    if entry:
        kpis.append(dbc.Col(components.kpi_card("Entry", f"${entry:.2f}"), md=4))
    if stop:
        kpis.append(dbc.Col(components.kpi_card("Stop Loss", f"${stop:.2f}",
                                                  delta_positive=False), md=4))
    if tp:
        kpis.append(dbc.Col(components.kpi_card("Take Profit", f"${tp:.2f}",
                                                  delta_positive=True), md=4))

    return dbc.Card(dbc.CardBody([
        html.Div([
            html.Span("Timing Recommendation",
                      style={"color": theme.MUTED, "fontSize": "11px",
                             "textTransform": "uppercase", "letterSpacing": "0.6px"}),
            html.Br(),
            html.Span(action, style={"color": color, "fontWeight": "700", "fontSize": "18px"}),
            html.Span(f"  {reason}", style={"color": theme.TEXT, "fontSize": "13px"}),
        ], className="mb-3"),
        dbc.Row(kpis, className="g-3") if kpis else html.Div(),
    ]), style={"borderLeft": f"3px solid {color}"}, className="mt-3 mb-3")


def _build_index_table(indexes: list[dict]) -> html.Div:
    rows = []
    for idx in indexes:
        c1d = idx.get("change_1d_pct")
        c5d = idx.get("change_5d_pct")
        c30d = idx.get("change_30d_pct")
        price = idx.get("price")
        rows.append({
            "Index": idx.get("name") or idx.get("symbol", ""),
            "Price": f"${price:.2f}" if price else "—",
            "1D %": f"{c1d:+.2f}%" if c1d is not None else "—",
            "5D %": f"{c5d:+.2f}%" if c5d is not None else "—",
            "30D %": f"{c30d:+.2f}%" if c30d is not None else "—",
            "Trend": "Above SMA50" if idx.get("above_sma50") else ("Below SMA50" if idx.get("above_sma50") is False else "—"),
        })

    return html.Div([
        html.H6("Market Index Overview",
                style={"color": theme.MUTED, "fontSize": "12px",
                       "textTransform": "uppercase", "letterSpacing": "0.6px", "marginTop": "16px"}),
        dash_table.DataTable(
            data=rows,
            columns=[{"name": c, "id": c} for c in ["Index", "Price", "1D %", "5D %", "30D %", "Trend"]],
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "#161b22", "color": theme.MUTED,
                "fontWeight": "600", "fontSize": "11px",
                "textTransform": "uppercase", "border": f"1px solid {theme.BORDER}",
            },
            style_cell={
                "backgroundColor": theme.CARD_BG, "color": theme.TEXT,
                "border": f"1px solid {theme.BORDER_LIGHT}",
                "padding": "8px 12px", "fontSize": "13px",
            },
            style_data_conditional=[
                {"if": {"filter_query": '{1D %} contains "+"', "column_id": "1D %"},
                 "color": theme.GREEN},
                {"if": {"filter_query": '{1D %} contains "-"', "column_id": "1D %"},
                 "color": theme.RED},
                {"if": {"filter_query": '{5D %} contains "+"', "column_id": "5D %"},
                 "color": theme.GREEN},
                {"if": {"filter_query": '{5D %} contains "-"', "column_id": "5D %"},
                 "color": theme.RED},
                {"if": {"filter_query": '{30D %} contains "+"', "column_id": "30D %"},
                 "color": theme.GREEN},
                {"if": {"filter_query": '{30D %} contains "-"', "column_id": "30D %"},
                 "color": theme.RED},
            ],
        ),
    ], className="mt-3")


def _build_summary_markdown(result: dict) -> str:
    """Build a predictions.md-style markdown summary from the API result."""
    ticker = result.get("ticker", "")
    direction = (result.get("direction") or "neutral").upper()
    confidence = result.get("confidence", 0.0) or 0.0
    price = result.get("current_price") or 0.0
    target = result.get("price_target")
    target_date = result.get("target_date")
    risk = (result.get("risk_level") or "medium").title()
    factors = result.get("factors") or []
    timing = result.get("timing") or {}
    meta = result.get("meta") or {}
    levels = result.get("levels") or {}
    timeframe = meta.get("timeframe", "")
    narrative = meta.get("ai_narrative") or meta.get("narrative")

    bullish = sorted([f for f in factors if (f.get("points") or 0) > 0],
                     key=lambda f: -(f.get("points") or 0))[:8]
    bearish = sorted([f for f in factors if (f.get("points") or 0) < 0],
                     key=lambda f: (f.get("points") or 0))[:8]

    out: list[str] = []
    title = f"{ticker} ({timeframe})" if timeframe else ticker
    out.append(f"## {title}")
    out.append("")
    out.append("### Prediction Summary")
    out.append("")
    out.append("| Field | Value |")
    out.append("| --- | --- |")
    out.append(f"| Direction | **{direction}** |")
    out.append(f"| Confidence | **{confidence * 100:.1f}%** |")
    out.append(f"| Current Price | ${price:,.2f} |")
    if target is not None and price:
        chg = (target - price) / price * 100.0
        out.append(f"| Price Target | ${target:,.2f} ({chg:+.2f}%) |")
    if target_date:
        out.append(f"| Target Date | {target_date} |")
    out.append(f"| Risk Level | {risk} |")
    net_points = sum((f.get("points") or 0) for f in factors)
    if factors:
        out.append(f"| Net score | {net_points:+d} pts across {len(factors)} factors |")
    out.append("")

    if bullish:
        out.append("### Key Bullish Factors")
        out.append("")
        for i, f in enumerate(bullish, 1):
            detail = f.get("detail") or f.get("category", "")
            out.append(f"{i}. **{f.get('name', '')}** — {detail} _({(f.get('points') or 0):+d} pts)_")
        out.append("")

    if bearish:
        out.append("### Key Risk Factors / Bearish Signals")
        out.append("")
        for i, f in enumerate(bearish, 1):
            detail = f.get("detail") or f.get("category", "")
            out.append(f"{i}. **{f.get('name', '')}** — {detail} _({(f.get('points') or 0):+d} pts)_")
        out.append("")

    pivots = levels.get("pivots") or {}
    if pivots:
        out.append("### Technical Levels to Watch")
        out.append("")
        out.append("| Level | Price |")
        out.append("| --- | --- |")
        for label, key in [("R2", "r2"), ("R1", "r1"), ("**PP**", "pp"), ("S1", "s1"), ("S2", "s2")]:
            v = pivots.get(key)
            if v is not None:
                bold = "**" if label.startswith("**") else ""
                out.append(f"| {label} | {bold}${v:,.2f}{bold} |")
        out.append("")

    fib = levels.get("fibonacci") or {}
    fib_levels = fib.get("levels") or {}
    if fib_levels:
        out.append("### Fibonacci Retracement Levels")
        out.append("")
        lo, hi = fib.get("low"), fib.get("high")
        if lo is not None and hi is not None:
            out.append(f"_Range: ${lo:,.2f} → ${hi:,.2f}_")
            out.append("")
        out.append("| Level | Price |")
        out.append("| --- | --- |")
        for label, val in fib_levels.items():
            out.append(f"| {label} | ${val:,.2f} |")
        out.append("")

    if timing:
        out.append("### Timing Recommendation")
        out.append("")
        out.append(f"**Action:** `{timing.get('action', 'WAIT')}`")
        out.append("")
        if timing.get("reason"):
            out.append(f"**Rationale:** {timing.get('reason')}")
            out.append("")
        rows: list[tuple[str, str]] = []
        if timing.get("entry_price") is not None:
            rows.append(("Entry Price", f"${timing['entry_price']:,.2f}"))
        if timing.get("stop_loss") is not None:
            rows.append(("Stop Loss", f"${timing['stop_loss']:,.2f}"))
        if timing.get("take_profit") is not None:
            rows.append(("Take Profit", f"${timing['take_profit']:,.2f}"))
        rows.append(("Time Horizon", timing.get("time_horizon", "1w")))
        out.append("| Field | Value |")
        out.append("| --- | --- |")
        for k, v in rows:
            out.append(f"| {k} | {v} |")
        out.append("")

    out.append("### Analysis")
    out.append("")
    out.append(narrative if narrative else _default_narrative(result, bullish, bearish))
    out.append("")

    return "\n".join(out)


def _default_narrative(result: dict, bullish: list[dict], bearish: list[dict]) -> str:
    ticker = result.get("ticker", "")
    direction = (result.get("direction") or "neutral").lower()
    confidence = result.get("confidence", 0.0) or 0.0
    price = result.get("current_price") or 0.0
    target = result.get("price_target")
    risk = (result.get("risk_level") or "medium").lower()
    timeframe = (result.get("meta") or {}).get("timeframe", "window")

    parts = [
        f"The technical model projects a **{direction}** stance on {ticker} "
        f"with {confidence * 100:.0f}% confidence over the coming {timeframe}."
    ]
    if bullish:
        parts.append("Bullish support comes from " + ", ".join(f["name"] for f in bullish[:3]) + ".")
    if bearish:
        parts.append("Key risks include " + ", ".join(f["name"] for f in bearish[:3]) + ".")
    if target is not None and price:
        delta = (target - price) / price * 100.0
        parts.append(
            f"The projected price target is ${target:,.2f} ({delta:+.2f}% from current), "
            f"assuming the scored signals continue to dominate; position sizing should respect "
            f"the {risk} volatility regime."
        )
    return " ".join(parts)
