# Trading System Guide

## Table of Contents

1. [Installation](#installation)
2. [Launch the Web UIs](#launch-the-web-uis)
3. [Streamlit UI](#streamlit-ui)
4. [Dash UI](#dash-ui)
5. [CLI Usage](#cli-usage)
6. [REST API](#rest-api)
7. [Python API](#python-api)
8. [Backtesting](#backtesting)
9. [Live / Paper Trading](#live--paper-trading)
10. [Watchlist Scanning](#watchlist-scanning)
11. [Configuration Guide](#configuration-guide)
12. [AI Integration](#ai-integration)
13. [Extending the System](#extending-the-system)

---

## Installation

```bash
git clone <repo>
cd prediction-trading
uv sync
cp .env.example .env
# Add your Anthropic key to enable AI (optional):
# ANTHROPIC_API_KEY=sk-ant-...
```

Verify:
```bash
uv run pytest backend/tests/ -v   # 14 test files, all offline — no API key needed
uv run stock-predictor --tickers AAPL --no-ai
```

---

## Launch the Web UIs

Two web frontends are available. Both use the same prediction and risk engine.

| UI | Command | URL | Prerequisite |
|---|---|---|---|
| **Streamlit** | `make ui-dev` | `http://localhost:8501` | None (self-contained) |
| **Dash** | `make dash-dev` | `http://localhost:8050` | `make api-dev` must be running |

```bash
# Streamlit (standalone)
make ui-dev    # or: uv run streamlit run frontend/app.py

# Dash (needs API)
make api-dev   # Terminal 1 — FastAPI on :8000
make dash-dev  # Terminal 2 — Dash on :8050
```

### Feature comparison

| Feature | Streamlit UI | Dash UI |
|---|---|---|
| Backend dependency | Self-contained (calls Python directly) | Requires `make api-dev` running on `:8000` |
| Pages | 8 | 9 (adds **Analytics**) |
| Live polling | Meta-refresh (page reload) | Dash `dcc.Interval` callbacks (no full reload) |
| Theme | Light or dark (toggle in header) | **Auto / Dark / Light** (toggle in navbar; Auto follows OS preference) |
| Global status bar | Per-page `config_info_bar()` component | Single global bar between navbar and page content |
| State persistence | `st.session_state` (session) | `dcc.Store` (session / localStorage / memory) |
| AI model selector | Settings page | Per-prediction on Predict page |
| Launch command | `make ui-dev` | `make dash-dev` |

The **Dash UI** connects to the REST API and adds a dedicated **Analytics** page (confidence distribution, factor frequency, category heatmap, ticker scatter) not present in Streamlit.

---

## Streamlit UI

### Getting Started

**Header:** The app name appears at the top-left. A **🌙 Dark / ☀️ Light** toggle in the top-right switches the entire UI between a dark (`#0f1318` background) and light theme.

**Top navigation bar:** Eight icon+label buttons select the active page. The active page button is highlighted in green; inactive buttons show a gray border.

**Config Info Bar:** A one-line caption below the page title on every page except Settings shows: `Data source · Broker type · AI model` (or "AI disabled"). Use this to confirm your active configuration at a glance before running predictions or trades.

**Sidebar watchlist:** A persistent left sidebar shows a list of saved tickers with live price badges. Click **＋** to add a ticker; click **✕** to remove one. Clicking a ticker name navigates to the Predict page with that ticker pre-filled. The watchlist is saved to `watchlist.json` and survives page navigation and browser refreshes.

---

### Streamlit Dashboard (📊)

**Purpose:** Monitor your live or most recent portfolio — equity growth, open positions, and risk metrics — all in one view.

**Loading portfolio data (in priority order):**
1. Automatically reads from a running AutoTrader (if started on the Trading page in the same session).
2. Falls back to the results of a completed Backtest run in the same session.
3. Shows a file uploader — drag in a saved `results/live_*/portfolio_state.json`.

**Overview tab:**

| Widget | Description |
|---|---|
| Portfolio Value | Total equity (cash + unrealised positions), with return % vs initial capital |
| Cash Available | Uninvested cash balance |
| Day P&L | Intraday profit/loss in $ and as a % of initial capital |
| Open Positions | Count of open positions / max allowed (e.g., `2 / 5`) |
| Equity Curve | Plotly line chart with area fill; dashed initial-capital baseline; hoverable data points |
| Open Positions table | Ticker · Side · Qty · Entry $ · Current $ · Unrealised P&L $ · Return % · Stop $ · Target $ |
| Recent Trades table | Last 20 closed trades: Ticker · Side · Qty · Entry · Exit · P&L · Return % · Result (Win/Loss) · Reason |

**Risk tab:**

| Widget | Description |
|---|---|
| Max Drawdown % | Largest peak-to-trough equity decline |
| Win Rate % | Percentage of closed trades that were profitable |
| Profit Factor | Gross wins / gross losses (>1 = net positive) |
| Total Trades | Number of closed trades |
| Daily Loss vs Cap | Colored progress bar showing today's loss vs the 2% daily cap |
| Position Concentration | Horizontal bar chart: % of portfolio equity by ticker |

**Auto-refresh:** While the AutoTrader is running, the page refreshes every 15 seconds automatically.

---

### Streamlit Predict (🔮)

**Purpose:** Run a rule-based or AI-assisted prediction for a single ticker and explore the signal, timing, and price chart.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Ticker Symbol | Any valid ticker (e.g., `AAPL`) | Pre-filled from watchlist click |
| Timeframe | `1d` `1w` `1m` `3m` `6m` `ytd` `1y` `2y` `5y` | `1w` |
| Indicator Categories | multiselect: trend · momentum · volatility · volume · support · fundamental | all six |
| Enable AI (Claude) | toggle | off — requires `ANTHROPIC_API_KEY` in `.env` |
| 4H Confluence | toggle | off — fetches 1H OHLCV, resamples to 4H, adds up to ±1 bonus point |
| Save report | checkbox | off — writes `results/predict_*/predictions.md` + PNG |

Click **Run Prediction** (disabled until a ticker is entered).

**Signal tab** (first result tab):

- **Prediction card:** Direction badge (`BUY` / `SELL` / `HOLD`) + confidence % with progress bar; Current Price · Price Target (with % change) · Risk Level (Low/Medium/High); up to 5 Bullish Factors (▲) and 5 Bearish Factors (▼) with detail text.
- **Timing Recommendation card** (when available): Action label — one of `BUY NOW` · `BUY ON DIP` · `BREAKOUT ENTRY` · `SELL NOW` · `TRAILING STOP` · `HOLD` · `WAIT` — with color-coded badge; Entry $ · Stop Loss $ · Take Profit $.
- **Market Index table:** VIX, SPY, QQQ, DXY — Price · 1D % · 5D % · 30D % · Trend (↑ Above / ↓ Below SMA50). Green/red color-coded. Requires macro context (fetched automatically when AI is on or enriched context is available).

**Candlestick Chart tab:**

Interactive Plotly OHLC chart (last 120 bars):
- Bullish (green) / bearish (red) candles
- SMA20 (gold) and SMA50 (blue) overlays
- Entry price line (blue dot), stop loss line (red dash), take profit line (green dash) with labels
- Volume sub-panel below (bars colored per candle direction)

**Analysis Chart tab:**

Static multi-panel matplotlib PNG — the same image written to `results/` when "Save report" is checked. Shows price + target, confidence gauge, and category-conditional indicator panels.

**Session caching:** Results are stored in session state. Switching tabs or adjusting the page does not re-run the prediction. Click **Run Prediction** again to refresh.

---

### Streamlit Scanner (🔍)

**Purpose:** Screen a list of tickers simultaneously and surface the strongest BUY and SELL signals.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Watchlist | One ticker per line (textarea) | Sidebar watchlist tickers |
| Min Confidence | 0.00–1.00 (step 0.05) | 0.40 |
| Parallel Workers | 1–16 | 4 |
| Indicator Categories | multiselect: trend · momentum · volatility · volume · support · fundamental | all six |

Click **Scan Watchlist**. A spinner shows the count of tickers being processed.

**Results:**

- **4 summary cards:** Total Scanned · BUY count · SELL count · HOLD/below-threshold count.
- **Results table:** Ticker · Signal · Confidence % · Price $ · Top Factors (top-3 scoring factors). Sorted by confidence descending. Per-row errors shown in red.
- **CSV Export button:** Downloads the full results table as a `.csv` file.

**Note:** The scanner skips AI calls and chart generation — it is rule-based only. The news/macro/sector categories are not available from the UI multiselect; use the CLI (`--indicators`) for those. For a deeper analysis of any result, click that ticker in the sidebar watchlist to open it in Predict.

---

### Streamlit Backtest (📅)

**Purpose:** Simulate the prediction and risk engine over a historical date range and evaluate strategy performance.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Ticker | Any valid ticker | — |
| Start Date | Date picker | 1 year ago |
| End Date | Date picker | Today |
| Initial Capital ($) | Number input | 10,000 |
| Commission Per Trade ($) | Number input | 1.00 |

Click **Run Backtest** (validates end > start).

**Results — 8 KPI cards:**

Total Return % · Max Drawdown % · Win Rate % · Profit Factor · Total Trades · Avg Win $ · Avg Loss $ · Final Equity $

**Equity Curve tab:** Plotly area chart with initial capital baseline. Hover shows date and equity value.

**Candlestick + Trades tab:** Interactive OHLC chart (same as Predict) with trade markers overlaid — green triangle-up at each buy entry, red triangle-down at each sell exit.

**Trade Log tab:** Full scrollable table of every trade: Ticker · Side · Qty · Entry $ · Exit $ · P&L $ · Return % · Result (Win/Loss) · Reason (stop/target/end-of-data).

**Save Full Report button:** Writes `report.md` + four chart PNGs to `results/backtest_TICKER_YYYYMMDD_HHMMSS/`.

**Interpreting results:**
- Profit Factor > 1.5 is a reasonable baseline for a working strategy.
- Win rate alone is misleading — a 40% win rate with 3:1 R:R is net profitable.
- Max Drawdown drives position sizing: if uncomfortable, reduce `max_position_size_pct` in Settings.
- Compare against buy-and-hold over the same period for context.

---

### Streamlit Trading (⚡)

**Purpose:** Start, monitor, and stop the AutoTrader — a live paper-trading loop that runs predictions and places orders on a configurable cycle.

**Stopped state — start form:**

| Control | Values | Default |
|---|---|---|
| Tickers | One per line (textarea) | — |
| Cycle Interval | 60–3600 seconds | 300 (5 min) |
| Dry Run | toggle | on — signals only, no orders placed |
| Enforce Market Hours | toggle | off — when on, only trades 09:30–16:00 ET Mon–Fri |
| State File Path | text input | `results/live/portfolio_state.json` |

Click **Start AutoTrader**.

**Running state — live dashboard:**

- **Status card:** "🟢 Running — N cycles completed" + **Stop AutoTrader** button.
- **3 KPI cards:** Portfolio Value (with return %) · Cash Available · Open Positions count.
- **Equity Curve:** Plotly chart, updates each cycle.
- **Open Positions table:** same columns as Dashboard.
- **Last Cycle panel:** table of actions taken this cycle (Ticker · Action · Direction · Confidence · Price · Reason); errors expander shows per-ticker exceptions from the last cycle.
- **Error Log expander:** full error history across all cycles (last 20 entries).

**Auto-refresh:** The page reruns every 10 seconds while the AutoTrader is running.

**Threading:** AutoTrader runs in a daemon thread. Results are passed to the UI via a `queue.Queue`. The thread stops when you click **Stop AutoTrader** or when the Streamlit process exits. Reloading the browser page will show stale portfolio data until the next cycle completes and the queue is drained.

---

### Streamlit Portfolio Builder (🧱)

**Purpose:** Analyse a multi-ticker portfolio of stocks and ETFs for correlation, sector exposure, and diversification.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Tickers | One per line (stocks and/or ETFs) | `SPY QQQ XLK BND GLD` |
| Lookback Period | 30–1260 trading days | 252 (one year) |

Click **Analyze Portfolio**.

**Results:**

- **Holdings cards** (one per ticker): ETF badge or Stock badge · display name · for ETFs: category and expense ratio %.
- **Diversification Score:** 0–1 (higher = lower average pairwise correlation = better diversification). Green ≥ 0.5, orange ≥ 0.25, red < 0.25.
- **Correlation Matrix heatmap:** Pairwise return correlations color-coded: red (≥ 0.85 highly correlated) → orange (≥ 0.60) → light green (< 0.30) → light blue (negative).
- **Sector Exposure bar chart:** Equal-weighted GICS sector breakdown (horizontal bars, % weight).
- **Recommendations list:** Flags pairs with correlation > 0.85 as candidates for replacement; suggests sector gaps; warns on high expense ratios.

---

### Streamlit Alerts (🔔)

**Purpose:** Create price, confidence, and P&L triggers that fire when a condition is met, with a persistent log of all triggered alerts.

**Active Alerts tab:**

One card per alert: Ticker (bold) · Created timestamp (gray) · Trigger condition (color-coded green if "above"/"≥", red if "below"/"≤") · **✕ Delete** button.

**Check Alerts Now button:** Manually evaluates all active alerts against current prices via yfinance. Alerts that fire are moved to the Triggered Log and shown as toast notifications.

**Create Alert tab:**

| Field | Options |
|---|---|
| Ticker | Text input (default: AAPL) |
| Trigger Type | Price above · Price below · Confidence ≥ · Daily P&L ≥ · Daily P&L ≤ |
| Value | $ for price triggers; 0–100 for confidence/P&L % |

Click **Create Alert** → success toast.

**Triggered Log tab:** Last 50 triggered alerts (newest first): Ticker · Fired timestamp · Condition · Actual value at trigger. **Clear Log** button removes all entries.

**Persistence:** Alerts are saved to `alerts.json` in the working directory and survive page navigation and browser refreshes. They are **not** evaluated automatically in the background — use **Check Alerts Now** or pair with the Trading page for continuous monitoring.

---

### Streamlit Settings (⚙️)

**Purpose:** Configure all system parameters and save them to `config/default.yaml`.

The Config Info Bar does **not** appear on this page — Settings is where those values are set.

**Risk Profile section:**

Select a preset (Conservative / Moderate / Aggressive) and click **Apply Profile** to pre-fill the form fields below. Review the values before saving — Apply does not write to disk.

**Portfolio section:**

| Parameter | Range | Default |
|---|---|---|
| Initial Capital ($) | 1,000–10,000,000 | 10,000 |
| Max Concurrent Positions | 1–50 | 5 |
| Max Position Size (% of equity) | 1%–50% | 5% |
| Commission Per Trade ($) | 0–100 | 1.00 |

**Risk Management section:**

| Parameter | Range | Default |
|---|---|---|
| Max Daily Loss % (halt trigger) | 0.5%–10% | 2% |
| Min Risk:Reward Ratio | 0.5–10 | 1.5 |
| Stop Loss ATR Multiplier | 0.5–10 | 2.0 |
| Take Profit ATR Multiplier | 0.5–20 | 3.0 |

**Signal Settings section:**

| Parameter | Range | Default |
|---|---|---|
| Min Confidence Threshold | 0–1 | 0.40 |
| 4H Confluence Bonus (points) | 0–10 | 1 |
| AI Weight (0 = rule-only, 1 = AI-only) | 0–1 | 0.50 |

**Indicator Categories:** Multiselect of all nine categories (trend · momentum · volatility · volume · support · fundamental · news · macro · sector). Unchecking a category removes it from scoring, chart panels, and AI context.

**AI / Claude Settings:**

| Parameter | Options / Range | Default |
|---|---|---|
| Enable AI Predictor | toggle | off |
| Claude Model | claude-sonnet-4-6 · claude-opus-4-7 · claude-haiku-4-5-20251001 | claude-sonnet-4-6 |
| AI Prediction Timeframe | 1d 1w 1m 3m 6m ytd 1y 2y 5y | 1m |
| Max Response Tokens | 500–8,000 | 2,000 |

**Auto-Trader Settings:**

| Parameter | Range | Default |
|---|---|---|
| Cycle Interval (seconds) | 60–3600 | 300 |
| Dry Run (signals only) | toggle | off |
| Enforce Market Hours | toggle | off |
| Simulated Slippage (basis points) | 0–100 | 0 |

**Data Source:** yfinance (default) · alpaca · both. Selecting alpaca or both requires `ALPACA_API_KEY` and `ALPACA_API_SECRET` in `.env`.

**Broker:** paper (default) · alpaca.

**Save Settings button:** Writes all values to `config/default.yaml`. Changes take effect immediately for new predictions and scans. The AutoTrader must be stopped and restarted to pick up new settings.

---

## Dash UI

The Dash UI (`dash-frontend/`) is a real-time trading dashboard built with [Plotly Dash](https://dash.plotly.com/) and Bootstrap (DARKLY theme). It connects to the FastAPI backend at `http://localhost:8000` and provides nine pages covering prediction, scanning, analytics, live trading, backtesting, portfolio analysis, alerts, and configuration.

See the [feature comparison table](#feature-comparison) above for differences vs the Streamlit UI.

### Prerequisites

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

### Navigation & Layout

**Navbar** — A top navigation bar lists all nine pages (sorted by `order=`). On mobile, the nav collapses to a hamburger menu.

**Theme switcher** — A three-button group on the right side of the navbar:

| Button | Icon | Behaviour |
|---|---|---|
| **Auto** | half-circle | Follow `prefers-color-scheme` from the OS (default) |
| **Dark** | moon | Force dark theme (`data-bs-theme="dark"`) |
| **Light** | sun | Force light theme (`data-bs-theme="light"`) |

The selection persists in `localStorage` (`theme-store`). All Plotly charts re-render when the theme changes — every chart factory in `dash_ui/components.py` accepts an optional `plotly_layout=` kwarg, and pages pass `theme.get_plotly_layout(current_theme)` from the `current-theme-store`. CSS variables (`--theme-bg`, `--theme-card-bg`, `--theme-text`, …) defined in `dash_ui/theme.py:CUSTOM_CSS` keep cards, inputs, tables, and form controls in sync.

**Global status bar** — A compact bar between the navbar and the page content shows the active backend configuration (loaded once on app start via `GET /config/`):

| Field | Source | Badge color |
|---|---|---|
| **Data** | `data.source` | blue (`yfinance` / `alpaca` / `both`) |
| **Feed** | `data.interval` | cyan (`1d` / `1h` / `1m` / …) |
| **Model** | `ai.enabled` ? `ai.model` : `Rule-based` | green when AI enabled, grey otherwise |
| **Broker** | `broker.type` / `paper_trading` | grey for `Paper`, amber for `Alpaca`; bullet dot is green when **not** in dry-run, grey when dry-run |

If the API is unreachable on startup, the bar collapses to a red **API Offline** badge and pages show their own per-callback error states.

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

### Cross-Page State (dcc.Store)

Stores defined in `app.py` are global and shared across pages; page-scoped stores are declared inside the page layout:

| Store ID | Scope | Defined in | Written by | Read by | Contents |
|---|---|---|---|---|---|
| `scan-results-store` | session | `app.py` | Scanner | Analytics | Full scan result list |
| `predict-result-store` | session | `app.py` | Predict | Analytics | Last prediction result |
| `app-config-store` | session | `app.py` | startup callback | (status bar) | Config dict from `GET /config/` |
| `theme-store` | localStorage | `app.py` | navbar buttons | clientside callback | Theme preference: `"auto"` / `"dark"` / `"light"` |
| `current-theme-store` | memory | `app.py` | clientside callback | every chart-rendering callback | Resolved theme: `"dark"` or `"light"` |
| `alerts-store` | localStorage | `pages/alerts.py` | Alerts | Alerts | `{"active": [...], "triggered": [...]}` |
| `equity-history-store` | memory | `pages/home.py` | Dashboard | Dashboard | List of `{ts, equity}` snapshots |
| `bt-store` | session | `pages/backtest.py` | Backtest | Backtest | Backtest result metadata |

Scope semantics:

- **`localStorage`** — survives browser refresh, tab close, and machine reboot.
- **`session`** — clears when the browser tab is closed.
- **`memory`** — clears on every page reload (in-memory only).

---

### Dash Dashboard (`/`)

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

### Dash Predict (`/predict`)

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

**Result tabs** (rendered conditionally based on what the API returns):

| Tab | Always shown? | Contents |
|---|---|---|
| **Signal** | yes | Ticker · direction badge · confidence % · current price · price target with % change · risk level · confidence gauge · Timing Recommendation card · Market Index Overview table |
| **Factors (N)** | yes | Horizontal bar chart of top 15 factors by point score (green = bullish, red = bearish); tab label includes the total factor count |
| **Analysis** | when `ohlcv` returned | Multi-panel `analysis_chart`: candlestick with EMA/SMA overlays · entry/stop/target lines · support/resistance levels · volume bars · MACD · RSI · Stochastic. Fully zoom/pan-enabled (`scrollZoom: true`); 1200 px tall |
| **Fundamentals** | when `fundamentals` present | `fundamentals_chart` — two-panel bar chart: valuation ratios (P/E, P/B, P/S, EV/EBITDA, …) and growth/margin metrics (revenue growth, profit margin, ROE, …) |
| **Market** | when macro indexes present | `index_performance_chart` — grouped bar chart of VIX / SPY / QQQ / DXY across 1D · 5D · 30D % changes |
| **AI Narrative** | when AI enabled and text returned | Raw Claude narrative in monospace (`<pre>`) |

**Timing Recommendation card** (when available):

Shows action label — one of `BUY NOW` · `BUY ON DIP` · `BREAKOUT ENTRY` · `SELL NOW` · `TRAILING STOP` · `HOLD` · `WAIT` — with color-coded badge and Entry $ · Stop Loss $ · Take Profit $ KPIs.

**Market Index table** (when macro data available):

Index (VIX · SPY · QQQ · DXY) · Price · 1D % · 5D % · 30D % · Trend (↑/↓ relative to SMA50). Green/red color-coded.

---

### Dash Scanner (`/scanner`)

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

### Dash Analytics (`/analytics`) — Dash-only

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

### Dash Trading (`/trading`)

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

### Dash Backtest (`/backtest`)

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

**Interpreting results:** Same engine as the Streamlit Backtest page — see [Streamlit Backtest](#streamlit-backtest-) for guidance on profit factor, drawdown, and win-rate interpretation.

---

### Dash Alerts (`/alerts`)

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

### Dash Portfolio Builder (`/portfolio`)

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

### Dash Settings (`/settings`)

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

### Architecture Notes

- **Entry point:** `dash-frontend/app.py` — creates the `Dash` app with `use_pages=True` (auto-registers pages from `dash_ui/pages/`), injects `theme.CUSTOM_CSS`, mounts the global `dcc.Store` components, registers the **clientside theme-toggle callback**, loads the backend config once via a one-shot `dcc.Interval`, and exposes `server` for gunicorn.
- **API client:** `dash_ui/api.py` — all HTTP calls go through typed helper functions (10 s timeout for fast calls, 60 s for predict/scan/backtest). Includes `get_config()`, `predict()`, `predict_macro()`, `scan()`, `backtest()`, `trading_status()`, `trading_start()`, `portfolio_analyze()`.
- **Components:** `dash_ui/components.py` — factory functions for all reusable Plotly charts and Bootstrap cards. Every chart factory accepts an optional `plotly_layout=` kwarg so callbacks can pass a theme-aware layout from `current-theme-store`:

  | Function | Purpose |
  |---|---|
  | `status_bar(config_data, api_online)` | Global config-summary bar mounted in `app.py` |
  | `kpi_card(title, value, delta=, delta_positive=)` | Bootstrap card with label / value / optional colored delta |
  | `direction_badge(direction)` | Pill-shaped BUY/SELL/HOLD label |
  | `factor_bar_chart(factors, height=, plotly_layout=)` | Horizontal bar of top-N factors |
  | `confidence_gauge(direction, confidence, height=, plotly_layout=)` | Plotly indicator gauge |
  | `equity_line_chart(equity_points, height=, initial_capital=, plotly_layout=)` | Equity area chart with capital baseline |
  | `candlestick_chart(ohlcv, height=, entry=, stop=, target=, plotly_layout=)` | Compact OHLC + volume + level lines |
  | `analysis_chart(ohlcv, indicators, levels, timing=, height=, plotly_layout=)` | Full multi-panel technical chart (Predict tab) |
  | `fundamentals_chart(fundamentals, ticker=, plotly_layout=)` | Two-panel valuation / growth bars |
  | `index_performance_chart(indexes, plotly_layout=)` | Grouped 1D / 5D / 30D macro index bars |
  | `scan_results_table(results)` | Sortable scan results `DataTable` |

- **Theme:** `dash_ui/theme.py`
  - Color constants: `BG`, `CARD_BG`, `BORDER`, `GREEN`, `RED`, `BLUE`, `YELLOW`, `PURPLE`, `MUTED`, `TEXT`, plus `DIRECTION_COLORS` / `DIRECTION_LABELS` / `DIRECTION_BADGE_BG`.
  - `PLOTLY_DARK_LAYOUT` and `PLOTLY_LIGHT_LAYOUT` dicts applied to every chart.
  - `get_plotly_layout(theme_name: str)` selects the appropriate layout — pages call this with `current-theme-store` data.
  - `CUSTOM_CSS` defines CSS variables under `[data-bs-theme="dark"]` / `[data-bs-theme="light"]` and a `prefers-color-scheme: light` media query so Bootstrap, DataTables, dropdowns, inputs, and cards all switch colors instantly.
- **Pages:** Each file in `dash_ui/pages/` exports `layout` and registers callbacks. Pages declare `dash.register_page(__name__, path=..., name=..., order=...)`. Chart callbacks take `Input("current-theme-store", "data")` so every figure re-renders on theme change.

---

## CLI Usage

### `stock-predictor` — Prediction report

```bash
# Rule-based (no API key needed)
uv run stock-predictor --tickers AAPL --no-ai

# Multi-ticker with Claude AI
uv run stock-predictor --tickers AAPL TSLA NVDA --timeframe 1m

# Filter indicator categories (faster, fewer panels)
uv run stock-predictor --tickers MSFT --indicators trend momentum volatility

# Extended thinking budget
uv run stock-predictor --tickers GOOG --thinking-budget 10000
```

Output: `results/predict_YYYYMMDD_HHMMSS/predictions.md` + PNG charts

### `scan-watchlist` — Watchlist scan

```bash
# Scan tickers with default settings
uv run scan-watchlist AAPL MSFT NVDA TSLA GOOGL

# Filter by confidence and categories
uv run scan-watchlist AAPL TSLA NVDA --min-confidence 0.4 --indicators trend momentum

# Use more parallel workers
uv run scan-watchlist $(cat my_watchlist.txt | tr '\n' ' ') --workers 8
```

Output: Ranked table to stdout, sorted by confidence descending.

### `automated-trader` — Paper trading

```bash
# Single cycle, dry run (signals only)
uv run automated-trader --tickers AAPL TSLA --dry-run --once

# Continuous every 5 minutes, market hours only
uv run automated-trader --tickers AAPL MSFT NVDA --interval 300 --market-hours

# With AI signals
uv run automated-trader --tickers AAPL --ai --interval 600
```

Output: `results/live_YYYYMMDD_HHMMSS/portfolio_state.json` + `trades.csv`

---

## REST API

Start the server:

```bash
uv run uvicorn prediction_trading.api.main:app --reload
# Interactive docs at http://localhost:8000/docs
```

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check |
| `/predict/` | POST | Single-ticker prediction |
| `/scan/` | POST | Parallel watchlist scan |
| `/backtest/` | POST | Bar-by-bar backtest |
| `/trading/start` | POST | Initialise AutoTrader session |
| `/trading/status` | GET | Current AutoTrader state |

Example with `curl`:

```bash
curl -s -X POST http://localhost:8000/predict/ \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "lookback_days": 365}' | python3 -m json.tool
```

---

## Python API

The fastest path for scripting or Jupyter notebooks:

```python
from prediction_trading import PredictionTradingSystem

# Predict
system = PredictionTradingSystem("AAPL")
market = system.fetch()
pred = system.predict(market)
print(f"{pred.ticker}: {pred.direction} {pred.confidence:.0%} → ${pred.price_target:.2f}")

# Save chart + markdown report
out_dir = system.save_report(prediction=pred)
print(f"Report: {out_dir}")

# Backtest
system2 = PredictionTradingSystem("TSLA", initial_capital=25_000)
result = system2.backtest("2023-01-01", "2024-01-01")
print(result.summary())

# Multi-ticker scan
from prediction_trading.scanner import WatchlistScanner
scanner = WatchlistScanner(min_confidence=0.4, workers=8)
results = scanner.scan(["AAPL", "MSFT", "NVDA", "TSLA", "META"])
for r in results:
    print(f"{r.ticker}: {r.direction} {r.confidence:.0%}")
```

---

## Backtesting

### Via the UI

1. Go to **Backtest** page
2. Enter ticker, date range, capital, commission
3. Click **Run Backtest**
4. Review metrics (return%, max drawdown, win rate, profit factor)
5. Inspect equity curve and trade log
6. Click **Save Full Report** to write markdown + charts to `results/`

### Via the API

```python
from prediction_trading import PredictionTradingSystem

system = PredictionTradingSystem(
    "AAPL",
    initial_capital=10_000,
    config_path="config/default.yaml",
)
result = system.backtest("2022-01-01", "2024-01-01")
stats = result.summary()

print(f"Return:       {stats['return_pct']:+.2f}%")
print(f"Max Drawdown: {stats['max_drawdown_pct']:.2f}%")
print(f"Win Rate:     {stats['win_rate_pct']:.1f}%")
print(f"Profit Factor:{stats['profit_factor']:.2f}")
print(f"Total Trades: {stats['trades']}")

out = system.save_report(result=result)
print(f"Report: {out}")
```

### Interpreting results

- **Profit factor > 1.5** is a reasonable threshold for a working strategy.
- **Max drawdown** drives position sizing — if uncomfortable, lower `max_position_size_pct`.
- **Win rate** alone is misleading. A 40% win rate with 3:1 average R:R is very profitable.
- Compare against buy-and-hold over the same period for context.

---

## Live / Paper Trading

### Start via the UI

1. Go to **Trading** page
2. Enter tickers, interval, enable Dry Run for testing
3. Click **Start AutoTrader**
4. Monitor equity curve and cycle reports
5. Click **Stop AutoTrader** to halt

### Start via the CLI

```bash
# Paper trading, one cycle
uv run automated-trader --tickers AAPL MSFT --dry-run --once

# Continuous, every 5 minutes, persist state
uv run automated-trader --tickers AAPL MSFT NVDA --interval 300
```

### State persistence

Portfolio state is saved to `results/live_*/portfolio_state.json` after each cycle. If the process restarts, `StateStore.load_or_create()` restores open positions and cash balance. Trade history is appended to `trades.csv`.

### Switching to a real broker

Implement `BaseBroker`:

```python
from prediction_trading.trading.broker import BaseBroker, Order, Fill
from prediction_trading.trading.portfolio import Trade

class MyBroker(BaseBroker):
    def get_quote(self, ticker: str) -> float:
        return my_api.last_price(ticker)

    def place_order(self, order: Order) -> Fill | None:
        resp = my_api.submit_order(order.ticker, order.quantity, order.side)
        return Fill(ticker=order.ticker, price=resp.fill_price, ...)

    def close_position(self, ticker, reason, quote=None, when=None) -> Trade | None:
        ...

system = PredictionTradingSystem("AAPL")
trader = system.build_auto_trader(
    tickers=["AAPL", "MSFT"],
    broker=MyBroker(),
    dry_run=False,
)
trader.run()
```

---

## Watchlist Scanning

The scanner is optimised for fast screening — it skips chart generation and AI calls.

```python
from prediction_trading.scanner import WatchlistScanner

scanner = WatchlistScanner(
    categories=("trend", "momentum"),   # only score these categories
    lookback_days=180,
    min_confidence=0.35,
    workers=8,
)
results = scanner.scan([
    "AAPL", "MSFT", "NVDA", "TSLA", "META",
    "GOOGL", "AMZN", "JPM", "GS", "BAC",
])

# Results sorted by confidence descending
for r in results:
    if r.error:
        print(f"{r.ticker}: ERROR — {r.error}")
    else:
        factors = ", ".join(r.top_factors[:3])
        print(f"{r.ticker:6} {r.direction:8} {r.confidence:5.0%}  {factors}")
```

---

## Configuration Guide

All defaults live in `config/default.yaml`. Every value can be overridden at `PredictionTradingSystem` instantiation.

### Risk profiles

The UI Settings page offers three presets from `config/risk_profiles.yaml`:

| Profile | Position size | Daily loss limit | Min confidence | Min R:R |
|---|---|---|---|---|
| Conservative | 3% | 1% | 60% | 2.0 |
| Moderate (default) | 5% | 2% | 40% | 1.5 |
| Aggressive | 10% | 5% | 30% | 1.2 |

### Key parameters

| Parameter | Path in YAML | Effect |
|---|---|---|
| `initial_capital` | `portfolio.initial_capital` | Starting portfolio value |
| `max_positions` | `portfolio.max_positions` | Max concurrent open positions |
| `max_position_size_pct` | `portfolio.max_position_size_pct` | Max equity per position |
| `min_confidence` | `signals.min_confidence` | Signal strength gate (0–1) |
| `stop_loss_atr_mult` | `risk.stop_loss_atr_mult` | Stop = entry ± ATR × mult |
| `take_profit_atr_mult` | `risk.take_profit_atr_mult` | Target = entry ± ATR × mult |
| `max_daily_loss_pct` | `risk.max_daily_loss_pct` | Halt trading at this daily drawdown |
| `ai_weight` | `signals.ai_weight` | 0 = pure rule-based, 1 = pure AI |
| `multi_timeframe_bonus` | `signals.multi_timeframe_bonus` | Points added when weekly agrees |
| `categories` | `indicators.categories` | Which rule categories to run |

### Indicator categories

Filter to specific categories for faster runs or to test isolated signals:

```yaml
indicators:
  categories:
    - trend       # SMA/EMA/MACD/Golden Cross
    - momentum    # RSI/Stochastic
    - volatility  # Bollinger/ATR
    - volume      # OBV/Volume spike
    - support     # Pivot points/Trendlines
    - fundamental # P/E, ROE, margins…
    - news        # Headline sentiment, earnings beat/miss (requires internet)
    - macro       # VIX, yield curve, SPY trend (requires internet)
    - sector      # Sector ETF relative strength (requires internet)
    # Comment out any category to exclude it from scoring
```

---

## AI Integration

### Setup

Add to `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Enable in config:
```yaml
ai:
  enabled: true
  model: claude-sonnet-4-6
  timeframe: 1m
  max_tokens: 2000
```

Or pass to the system directly:
```python
system = PredictionTradingSystem("AAPL", enable_ai=True, api_key="sk-ant-...")
```

### How it works

1. System prompt (cached with `cache_control: ephemeral`) instructs Claude to call the `stock_prediction` tool.
2. Claude calls the tool → local code fetches data with `include_enriched=True` (adds news, macro, sector context) and runs `SignalScorer` → returns structured result with optional `news`, `macro`, `sector` dicts.
3. Second API call: Claude receives tool result and returns a narrative (≤500 words) that comments on news sentiment/earnings, VIX/yield-curve, and sector relative strength when those fields are present.
4. `UnifiedPredictor` blends the AI confidence with the rule-based score.

### Prompt caching

The system prompt is ~1 500 tokens and is cached after the first call. Subsequent calls for the same ticker in the same session hit the cache, reducing cost by ~90%. Cache TTL is 5 minutes.

### Timeframes

The `timeframe` parameter controls the prediction window: `1d`, `1w`, `1m`, `3m`, `6m`, `ytd`, `1y`, `2y`, `5y`.

---

## Extending the System

### Adding a new indicator category

1. Add the category name to `factor.py:ALL_CATEGORIES`.
2. Add a `_<category>_factors(self, df)` method to `SignalScorer` following the existing pattern.
3. Call it inside `SignalScorer.score()` with an `if "<category>" in self.categories:` guard.
4. Optionally add a chart panel to `PredictionChart.render()`.

### Adding a new indicator to an existing category

Add the rule inside the appropriate `_<category>_factors` method. Each rule should:
- Check that the required column exists in `df` (use `self._v(row.get("COL_NAME"))`)
- Return a `Factor` with an appropriate `points` value (1 for weak signals, 2 for strong crossovers)

### Implementing a real broker

See [Switching to a real broker](#switching-to-a-real-broker) above.

### Adding a new report format

Subclass `BaseReportWriter` and `BaseChart` from `prediction_trading/reporting/base.py`. Follow the pattern in `PredictionReportWriter` and `PredictionChart`.
