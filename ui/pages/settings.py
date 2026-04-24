"""Settings page — read/write config/default.yaml and apply risk profiles."""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from ui.state import ACTIVE_PROFILE, SETTINGS_DIRTY

_DEFAULT_CFG = Path("config/default.yaml")
_PROFILES_CFG = Path("config/risk_profiles.yaml")


def _load(path: Path) -> dict:
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {}


def _save(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def render() -> None:
    st.title("Settings")

    cfg = _load(_DEFAULT_CFG)
    profiles = _load(_PROFILES_CFG)

    portfolio = cfg.get("portfolio", {})
    risk = cfg.get("risk", {})
    signals = cfg.get("signals", {})
    indicators = cfg.get("indicators", {})
    ai = cfg.get("ai", {})
    trader = cfg.get("trader", {})

    # ── Risk Profile ──────────────────────────────────────────────────────────
    st.subheader("Risk Profile")
    profile_names = list(profiles.keys()) if profiles else ["moderate"]
    current_profile = st.session_state.get(ACTIVE_PROFILE, "moderate")
    profile_idx = profile_names.index(current_profile) if current_profile in profile_names else 0
    selected_profile = st.selectbox("Select Profile", profile_names, index=profile_idx)

    if selected_profile != "custom" and st.button("Apply Profile", type="primary"):
        p = profiles.get(selected_profile, {})
        portfolio.update(p.get("portfolio", {}))
        risk.update(p.get("risk", {}))
        signals.update(p.get("signals", {}))
        st.session_state[ACTIVE_PROFILE] = selected_profile
        st.success(f"Applied **{selected_profile}** profile. Adjust below and Save.")

    st.divider()

    # ── Portfolio ─────────────────────────────────────────────────────────────
    st.subheader("Portfolio")
    col1, col2 = st.columns(2)
    with col1:
        portfolio["initial_capital"] = st.number_input(
            "Initial Capital ($)", 1_000.0, 10_000_000.0,
            value=float(portfolio.get("initial_capital", 10_000.0)), step=1000.0,
        )
        portfolio["max_positions"] = st.number_input(
            "Max Concurrent Positions", 1, 50,
            value=int(portfolio.get("max_positions", 5)),
        )
    with col2:
        portfolio["max_position_size_pct"] = st.slider(
            "Max Position Size (% of equity)", 0.01, 0.50,
            value=float(portfolio.get("max_position_size_pct", 0.05)),
            format="%.2f",
        )
        portfolio["commission_per_trade"] = st.number_input(
            "Commission per Trade ($)", 0.0, 100.0,
            value=float(portfolio.get("commission_per_trade", 1.0)),
        )

    # ── Risk ──────────────────────────────────────────────────────────────────
    st.subheader("Risk Management")
    col3, col4 = st.columns(2)
    with col3:
        risk["max_daily_loss_pct"] = st.slider(
            "Max Daily Loss (% before halting)", 0.005, 0.10,
            value=float(risk.get("max_daily_loss_pct", 0.02)),
            format="%.3f",
        )
        risk["min_risk_reward"] = st.number_input(
            "Min Risk:Reward Ratio", 0.5, 10.0,
            value=float(risk.get("min_risk_reward", 1.5)),
            step=0.1,
        )
    with col4:
        risk["stop_loss_atr_mult"] = st.number_input(
            "Stop Loss ATR Multiplier", 0.5, 10.0,
            value=float(risk.get("stop_loss_atr_mult", 2.0)),
            step=0.5,
        )
        risk["take_profit_atr_mult"] = st.number_input(
            "Take Profit ATR Multiplier", 0.5, 20.0,
            value=float(risk.get("take_profit_atr_mult", 3.0)),
            step=0.5,
        )

    # ── Signals ───────────────────────────────────────────────────────────────
    st.subheader("Signal Settings")
    col5, col6 = st.columns(2)
    with col5:
        signals["min_confidence"] = st.slider(
            "Min Confidence Threshold", 0.0, 1.0,
            value=float(signals.get("min_confidence", 0.40)),
            step=0.05,
        )
        signals["multi_timeframe_bonus"] = st.number_input(
            "Multi-Timeframe Confluence Bonus (points)", 0, 10,
            value=int(signals.get("multi_timeframe_bonus", 2)),
        )
    with col6:
        signals["ai_weight"] = st.slider(
            "AI Weight in Fused Score (0=rule-only, 1=AI-only)", 0.0, 1.0,
            value=float(signals.get("ai_weight", 0.5)),
            step=0.05,
        )

    # ── Indicators ────────────────────────────────────────────────────────────
    _ALL_CATS = ["trend", "momentum", "volatility", "volume", "support", "fundamental"]
    st.subheader("Indicator Categories")
    indicators["categories"] = st.multiselect(
        "Active Categories",
        _ALL_CATS,
        default=indicators.get("categories") or _ALL_CATS,
        help="Controls which rules run, which chart panels render, and what the AI prompt includes.",
    )

    st.divider()

    # ── AI ────────────────────────────────────────────────────────────────────
    st.subheader("AI / Claude Settings")
    col7, col8 = st.columns(2)
    with col7:
        ai["enabled"] = st.toggle("Enable AI Predictor", value=bool(ai.get("enabled", False)))
        ai["model"] = st.selectbox(
            "Claude Model",
            ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
            index=0,
        )
    with col8:
        ai["timeframe"] = st.selectbox(
            "AI Prediction Timeframe",
            ["1d", "1w", "1m", "3m", "6m", "ytd", "1y", "2y", "5y"],
            index=1,
        )
        ai["max_tokens"] = st.number_input(
            "Max Response Tokens", 500, 8000,
            value=int(ai.get("max_tokens", 2000)),
            step=500,
        )

    # ── Trader ────────────────────────────────────────────────────────────────
    st.subheader("Auto-Trader Settings")
    col9, col10 = st.columns(2)
    with col9:
        trader["interval_seconds"] = st.number_input(
            "Cycle Interval (seconds)", 60, 3600,
            value=int(trader.get("interval_seconds", 300)),
            step=60,
        )
        trader["dry_run"] = st.toggle(
            "Dry Run (signals only, no orders)", value=bool(trader.get("dry_run", False)),
        )
    with col10:
        trader["enforce_market_hours"] = st.toggle(
            "Enforce Market Hours (9:30–16:00 ET Mon–Fri)",
            value=bool(trader.get("enforce_market_hours", False)),
        )
        trader["slippage_bps"] = st.number_input(
            "Simulated Slippage (basis points)", 0.0, 100.0,
            value=float(trader.get("slippage_bps", 0.0)),
        )

    st.divider()
    if st.button("Save Settings", type="primary"):
        cfg["portfolio"] = portfolio
        cfg["risk"] = risk
        cfg["signals"] = signals
        cfg["indicators"] = indicators
        cfg["ai"] = ai
        cfg["trader"] = trader
        _save(_DEFAULT_CFG, cfg)
        st.session_state[SETTINGS_DIRTY] = False
        st.success("Settings saved to `config/default.yaml`. Restart the app to apply to running systems.")
