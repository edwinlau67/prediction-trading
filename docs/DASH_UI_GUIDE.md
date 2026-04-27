# Dash Web UI Guide

## Overview

The Dash UI (`dash-frontend/`) is a real-time trading dashboard built with [Plotly Dash](https://dash.plotly.com/) and Bootstrap (DARKLY theme). It connects to the FastAPI backend at `http://localhost:8000` and provides nine pages covering prediction, scanning, analytics, live trading, backtesting, portfolio analysis, alerts, and configuration.

**Comparison with the Streamlit UI (`frontend/`):**

| Feature | Streamlit UI | Dash UI |
|---|---|---|
| Backend dependency | Self-contained (calls Python directly) | Requires `make api-dev` running on `:8000` |
| Pages | 8 | 9 (adds **Analytics**) |
| Live polling | Meta-refresh (page reload) | Dash `dcc.Interval` callbacks (no full reload) |
| Theme | Light or dark (toggle in header) | Dark only |
| State persistence | `st.session_state` (session) | `dcc.Store` (session/localStorage) |
| AI model selector | Settings page | Per-prediction on Predict page |
| Launch command | `make ui-dev` | `make dash-dev` |

---

## Prerequisites

The Dash UI is a pure front-end that calls the REST API. The backend must be running before you open the UI:

```bash
# Terminal 1 — start the API
make api-dev
# → http://localhost:8000  (keep this running)

# Terminal 2 — start the Dash UI
make dash-dev
# → http://localhost:8050
```

Without the API running, all pages will show "API unavailable" errors.

---

## Navigation & Layout

**Navbar** — A top navigation bar lists all nine pages (sorted by order). On mobile, the nav collapses to a hamburger menu.

**Color conventions** throughout the UI:

| Color | Meaning |
|---|---|
| Green `#26d96a` | Bullish / BUY / profit / up |
| Red `#ff6464` | Bearish / SELL / loss / down |
| Blue `#58a6ff` | Neutral / HOLD / info |
| Yellow `#f0b429` | Warning / elevated risk |
| Purple `#c084fc` | Secondary info |
| Muted `#b0b8c4` | Neutral text / N/A |

---

## Cross-Page State (dcc.Store)

Some stores are global (defined in `app.py`) and shared across pages:

| Store ID | Scope | Written by | Read by | Contents |
|---|---|---|---|---|
| `scan-results-store` | session | Scanner | Analytics | Full scan result list |
| `predict-result-store` | session | Predict | Analytics | Last prediction result |
| `alerts-store` | localStorage | Alerts | Alerts | `{"active": [...], "triggered": [...]}` |
| `equity-history-store` | memory | Dashboard | Dashboard | List of `{t, equity}` snapshots |
| `bt-store` | session | Backtest | Backtest | Backtest result metadata |

`localStorage` stores survive browser refresh; `session` stores clear on tab close; `memory` stores clear on page reload.

---

## Page Reference

### 1. Dashboard (`/`)

**Purpose:** Real-time portfolio monitor. Polls the AutoTrader every 10 seconds via `/trading/status`.

**Status banner:** Appears when AutoTrader is running — shows tickers and running/stopped state.

**KPI row:**

| Card | Description |
|---|---|
| Portfolio Equity | Total equity (cash + unrealised positions) |
| Cash Available | Uninvested cash balance |
| Open Positions | Count of open positions |
| Status | Running (green) or Stopped (muted) |

**Equity curve:** Accumulates up to 360 data points (1 hour at 10-second intervals) from live polling. Resets on page reload.

**Tabs:**

| Tab | Contents |
|---|---|
| **Open Positions** | Ticker · Side · Qty · Entry $ · Stop $ · Target $ · Unrealised P&L $ |
| **Recent Trades** | Ticker · Side · Qty · Entry $ · Exit $ · P&L $ · Return % · Exit Time · Reason |
| **Risk** | Win Rate · Profit Factor · Total Trades · Cycles · Max Drawdown % |

The Dashboard is read-only — use the **Trading** page to start or stop the AutoTrader.

---

### 2. Predict (`/predict`)

**Purpose:** Run a rule-based or AI-assisted prediction for a single ticker.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Ticker Symbol | Text input (auto-uppercased) | — |
| Timeframe | `1d` `1w` `1m` `3m` `6m` `1y` `2y` `5y` | `1w` |
| Enable AI (Claude) | Toggle | off |
| Claude Model | Sonnet 4.6 · Opus 4.7 · Haiku 4.5 | Sonnet 4.6 |
| 4H Confluence | Toggle | off |
| Indicator Categories | Multiselect (all 9 available) | all |

Click **Run Prediction**. Results are stored in `predict-result-store` for use by the Analytics page.

**Result tabs:**

| Tab | Contents |
|---|---|
| **Signal** | Direction badge (BUY/SELL/HOLD) · Confidence % · Current Price · Price Target (with % change) · Risk Level · Confidence gauge · Timing Recommendation card · Market Index table |
| **Factors** | Horizontal bar chart of top 15 factors by point score (green = bullish, red = bearish) |
| **AI Narrative** | Raw Claude narrative in monospace (only shown when AI is enabled and returned text) |
| **Candlestick** | Interactive OHLCV chart with entry/stop/target lines and volume sub-panel |

**Timing Recommendation card** (when available):

Shows action label — one of `BUY NOW` · `BUY ON DIP` · `BREAKOUT ENTRY` · `SELL NOW` · `TRAILING STOP` · `HOLD` · `WAIT` — with color-coded badge and Entry $ · Stop Loss $ · Take Profit $ KPIs.

**Market Index table** (when macro data available):

Index (VIX · SPY · QQQ · DXY) · Price · 1D % · 5D % · 30D % · Trend (↑/↓ relative to SMA50). Green/red color-coded.

---

### 3. Scanner (`/scanner`)

**Purpose:** Screen a list of tickers in parallel and surface the strongest signals.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Watchlist | One ticker per line (textarea) | AAPL MSFT NVDA TSLA GOOGL AMZN META |
| Min Confidence | 0.00–1.00 (step 0.05) | 0.40 |
| Parallel Workers | 1–16 | 4 |

Click **Scan Now** to run. Results are stored in `scan-results-store` for the Analytics page.

**Summary KPIs:** Total Scanned · BUY count · SELL count · HOLD count.

**Results table:** Ticker · Direction badge · Confidence % · Price $ · Top Factors (comma-separated) · Error (if failed, in red). Sortable and filterable.

**Export CSV:** Downloads the full results table as a `.csv` file.

**Auto-refresh toggle:** When enabled, re-scans automatically every 30 seconds.

---

### 4. Analytics (`/analytics`) — Dash-only

**Purpose:** Visualize signal patterns from data collected by the Scanner and Predict pages in the current session. This page is unique to the Dash UI.

Reads from `scan-results-store` (all scanner results) and `predict-result-store` (last prediction), merges them, and applies filters.

**Filters:**

| Control | Values | Default |
|---|---|---|
| Min Confidence | 0.00–1.00 | 0.00 |
| Direction | Checklist: BUY · SELL · HOLD | all checked |

**Chart tabs:**

| Tab | Chart Type | What It Shows |
|---|---|---|
| **Confidence Distribution** | Histogram (overlay by direction) | Spread of confidence values — BUY green, SELL red, HOLD muted |
| **Direction Breakdown** | Donut pie | Count of bullish / bearish / neutral signals |
| **Factor Frequency** | Horizontal bar (top 20) | Most frequently scored factors across all tickers; bullish keywords green, bearish red |
| **Category Heatmap** | Grid heatmap | Rows = 9 indicator categories, columns = tickers, cells = net factor points; red (bearish) to green (bullish) |
| **Ticker Confidence** | Scatter plot | Tickers on x-axis, confidence on y-axis, sized by confidence, labeled BUY/SELL/HOLD |

**Note:** This page requires data from at least one Scan or Predict run in the current session. If both stores are empty, a prompt directs you to the Scanner or Predict page.

---

### 5. Trading (`/trading`)

**Purpose:** Start and monitor the AutoTrader — a live paper-trading loop that runs predictions and places orders on a configurable cycle.

**Stopped state — start form:**

| Control | Values | Default |
|---|---|---|
| Tickers | One per line (textarea) | AAPL MSFT NVDA |
| Initial Capital ($) | Number input | 10,000 |
| Dry Run | Toggle | on — signals only, no orders placed |
| Enforce Market Hours | Toggle | off — when on, only trades 09:30–16:00 ET Mon–Fri |
| Cycle Interval | Slider 60–3600 s | 300 (5 min) |
| State File Path | Text input (optional) | — |

Click **Start AutoTrader**. The API starts an AutoTrader session via `POST /trading/start`.

**Running state:**

- **Status banner:** "AutoTrader Running — N ticker(s): AAPL, MSFT, NVDA | Cycles: N"
- **KPI row:** Portfolio Equity · Cash · Open Positions · Live badge
- **Reset UI View** button: Clears the running state in the Dash UI (does not stop the backend — requires API restart to fully stop)
- **Open Positions table:** Ticker · Side · Qty · Entry $ · Stop $ · Target $

**Last Cycle panel:**

- Timestamp range (started\_at → finished\_at)
- **Actions table:** Ticker · Action (OPEN / CLOSE / ERROR, color-coded) · Direction · Confidence · Price $ · Reason
- **Errors section** (if any): Error messages in red

Live polling every 10 seconds via `dcc.Interval`.

---

### 6. Backtest (`/backtest`)

**Purpose:** Simulate the prediction and risk engine over a historical date range.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Ticker | Text input | — |
| Start Date | Date picker | 2023-01-01 |
| End Date | Date picker | 2024-12-31 |
| Initial Capital ($) | Number input (min 1,000) | 10,000 |
| Commission Per Trade ($) | Number input | 1.00 |

Click **Run Backtest**.

**Results — 8 KPI cards (2 rows):**

Row 1: Total Return % (color-coded) · Max Drawdown % · Win Rate % · Profit Factor

Row 2: Total Trades · Avg Win $ · Avg Loss $ · Final Equity $

**Result tabs:**

| Tab | Contents |
|---|---|
| **Equity Curve** | Plotly area chart with initial capital baseline; hover shows date and equity value |
| **Candlestick + Trades** | Interactive OHLC chart with trade markers — green ▲ at buy entries, red ▼ at sell exits |
| **Trade Log** | Sortable DataTable: Ticker · Side · Qty · Entry $ · Exit $ · P&L $ · Return % · Result (Win/Loss colored) · Reason |

**Interpreting results:** See the Streamlit guide (same engine) in [`TRADING_SYSTEM_GUIDE.md`](TRADING_SYSTEM_GUIDE.md#4-backtest-).

---

### 7. Alerts (`/alerts`)

**Purpose:** Create price, confidence, and P&L triggers that fire when a condition is met. Alert state persists in browser localStorage via `alerts-store`.

**Tabs:**

**Active Alerts tab:**

One card per active alert showing: Ticker · Alert type · Threshold value · Created timestamp · **✕ Delete** button.

**Check Alerts Now** button: Evaluates all active alerts against current prices via yfinance. Alerts that fire move to the Triggered Log.

**Create Alert tab:**

| Field | Options |
|---|---|
| Ticker | Text input |
| Trigger Type | Price above · Price below · Confidence ≥ · Daily P&L ≥ · Daily P&L ≤ |
| Value | $ for price; 0–1 for confidence; % for P&L |

Click **Create Alert** to add.

**Triggered Log tab:**

Last 50 triggered alerts (newest first): Ticker · Fired At · Trigger Type · Threshold · Actual value at trigger. **Clear Log** button removes all entries.

**Persistence:** The `alerts-store` uses `localStorage` — alerts survive browser refresh and tab close. They are **not** evaluated in the background automatically; use **Check Alerts Now** or the Trading page for continuous monitoring.

---

### 8. Portfolio Builder (`/portfolio`)

**Purpose:** Analyse a multi-ticker portfolio of stocks and ETFs for correlation, sector exposure, and diversification quality.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Tickers | One per line | SPY QQQ XLK BND GLD |
| Lookback Days | 30–1260 | 252 (one year) |

Click **Analyze Portfolio**. Calls `POST /portfolio/analyze`.

**Results:**

**Holdings cards** (one per ticker): ETF badge (blue) or Stock badge (purple) · display name · category · expense ratio (for ETFs).

**Diversification Score:** 0–1 (higher = lower average pairwise correlation = better diversification). Green ≥ 0.5 · Yellow ≥ 0.25 · Red < 0.25.

**Correlation Heatmap:** Pairwise return correlations — red (≥ 0.85, highly correlated) fading through yellow (neutral) to green (< 0.30, low correlation).

**Sector Exposure:** Horizontal bar chart showing equal-weighted GICS sector breakdown (% weight).

**Recommendations:** Bootstrap alerts (warning / success / info) flagging high-correlation pairs, missing sector diversification, and high expense ratios.

---

### 9. Settings (`/settings`)

**Purpose:** Read and write all backend configuration via the `/config/` API endpoints. Changes apply to the next prediction, scan, or backtest run. The AutoTrader must be restarted to pick up new settings.

**Load behavior:** On page mount a hidden interval fires once to `GET /config/` and populates all fields from the returned config dict.

**Save behavior:** Click **Save Settings** to rebuild the config dict and `PUT /config/`. A success or error alert is shown. A note reminds you to restart the API server to apply broker/data-source changes.

**Accordion sections:**

| Section | Parameters |
|---|---|
| **Portfolio** | Initial Capital · Max Positions · Max Position Size % · Commission |
| **Risk Management** | Max Daily Loss % · Min Risk:Reward · Stop Loss ATR Multiplier · Take Profit ATR Multiplier |
| **Signal Settings** | Min Confidence · AI Weight (0 = rule-only, 1 = AI-only) · Multi-Timeframe Bonus |
| **Indicator Categories** | Multiselect of all 9 categories (controls which rules run, chart panels render, and AI context reports) |
| **AI / Claude Settings** | Enable AI toggle · Claude Model · AI Timeframe · Max Response Tokens |
| **Auto-Trader** | Cycle Interval (s) · Dry Run · Enforce Market Hours · Simulated Slippage (bps) |
| **Data Source** | OHLCV source: yfinance · alpaca · both |
| **Broker** | Broker type: paper · alpaca · Paper Trading Mode toggle |

---

## Architecture Notes

- **Entry point:** `dash-frontend/app.py` — creates the `Dash` app with `use_pages=True` (auto-registers pages from `dash_ui/pages/`), injects `theme.CUSTOM_CSS`, mounts global `dcc.Store` components, and exposes `server` for gunicorn.
- **API client:** `dash_ui/api.py` — all HTTP calls go through typed helper functions (10 s timeout for fast calls, 60 s for predict/scan/backtest).
- **Components:** `dash_ui/components.py` — factory functions for all reusable Plotly charts and Bootstrap cards (`kpi_card`, `direction_badge`, `factor_bar_chart`, `confidence_gauge`, `equity_line_chart`, `candlestick_chart`, `scan_results_table`).
- **Theme:** `dash_ui/theme.py` — color palette constants and `PLOTLY_DARK_LAYOUT` dict applied to every chart.
- **Pages:** Each file in `dash_ui/pages/` exports `layout` (a Dash layout tree) and registers callbacks. Pages declare `dash.register_page(__name__, path=..., name=..., order=...)`.
