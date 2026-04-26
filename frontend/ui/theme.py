"""CSS injection for light/dark themes in the Streamlit UI."""
import streamlit as st

_DARK_CSS = """
<style>
/* ── Global dark background ─────────────────────────────────────── */
html, body, [data-testid="stApp"] {
    background-color: #0f1318 !important;
    color: #e8edf3 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* ── Hide Streamlit chrome ──────────────────────────────────────── */
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ── Main content area ──────────────────────────────────────────── */
[data-testid="stAppViewContainer"] > .main > .block-container {
    padding-top: 0.5rem !important;
    max-width: 1400px;
}

/* ── Header bar ─────────────────────────────────────────────────── */
.pt-header {
    display: flex;
    align-items: center;
    padding: 0.6rem 0 0.4rem 0;
    border-bottom: 1px solid #2d333b;
    margin-bottom: 0.25rem;
}
.pt-logo {
    font-size: 1.25rem;
    font-weight: 700;
    color: #26d96a;
    letter-spacing: -0.3px;
}
.pt-nav-divider {
    border-bottom: 1px solid #2d333b;
    margin: 0.3rem 0 0.8rem 0;
}

/* ── Navigation buttons ─────────────────────────────────────────── */
[data-testid="stButton"] button {
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.35rem 0.5rem !important;
    transition: all 0.15s ease !important;
}
[data-testid="stButton"] button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #3d444d !important;
    color: #b0b8c4 !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
    background: #1c2128 !important;
    border-color: #58a6ff !important;
    color: #e8edf3 !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: #26d96a !important;
    border: 1px solid #26d96a !important;
    color: #0d1117 !important;
    font-weight: 700 !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background: #1fc45e !important;
}

/* ── Cards ──────────────────────────────────────────────────────── */
.pt-card {
    background: #1c2128;
    border: 1px solid #3d444d;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
}
.pt-card-label {
    font-size: 0.72rem;
    color: #b0b8c4;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 0.2rem;
}
.pt-card-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #e8edf3;
    font-variant-numeric: tabular-nums;
    line-height: 1.2;
}
.pt-card-delta-pos {
    font-size: 0.85rem;
    color: #26d96a;
    font-weight: 600;
}
.pt-card-delta-neg {
    font-size: 0.85rem;
    color: #ff6464;
    font-weight: 600;
}
.pt-card-delta-neutral {
    font-size: 0.85rem;
    color: #b0b8c4;
    font-weight: 600;
}

/* ── Direction badges ───────────────────────────────────────────── */
.badge-buy {
    background: #1a4731; color: #26d96a;
    padding: 3px 10px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 700;
    border: 1px solid #26d96a;
}
.badge-sell {
    background: #4a1a1a; color: #ff6464;
    padding: 3px 10px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 700;
    border: 1px solid #ff6464;
}
.badge-hold {
    background: #2d333b; color: #d0d8e4;
    padding: 3px 10px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 700;
    border: 1px solid #5a6374;
}

/* ── Inputs, selects ────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
    background: #1c2128 !important;
    border-color: #3d444d !important;
    color: #e8edf3 !important;
    border-radius: 6px !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #1c2128 !important;
    border-color: #3d444d !important;
    color: #e8edf3 !important;
}
[data-testid="stMultiSelect"] > div > div {
    background: #1c2128 !important;
    border-color: #3d444d !important;
    color: #e8edf3 !important;
}
[data-testid="stTextArea"] textarea {
    background: #1c2128 !important;
    border-color: #3d444d !important;
    color: #e8edf3 !important;
}

/* ── Sliders ─────────────────────────────────────────────────────── */
[data-testid="stSlider"] > div > div > div > div {
    background: #26d96a !important;
}

/* ── DataFrames ─────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #3d444d !important;
    border-radius: 8px !important;
    overflow: hidden;
}
.dvn-scroller { background: #1c2128 !important; }

/* ── Inline HTML tables (trade log) ─────────────────────────────── */
table.dataframe { width:100%; border-collapse:collapse; font-size:0.84rem; }
table.dataframe thead tr th {
    padding:6px 10px; text-align:left !important;
    border-bottom:2px solid #3d444d;
    color:#b0b8c4; font-size:0.74rem;
    text-transform:uppercase; letter-spacing:0.5px; font-weight:600;
}
table.dataframe tbody tr td { padding:5px 10px; border-bottom:1px solid #2d333b; color:#e8edf3; }
table.dataframe tbody tr:hover td { background:#1c2128; }

/* ── Expanders ──────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #1c2128 !important;
    border: 1px solid #3d444d !important;
    border-radius: 8px !important;
}

/* ── Dividers ───────────────────────────────────────────────────── */
hr { border-color: #2d333b !important; }

/* ── Alerts / info boxes ─────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
}

/* ── Tab styling ─────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tab"] {
    color: #b0b8c4 !important;
    font-weight: 500;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #26d96a !important;
    border-bottom-color: #26d96a !important;
}

/* ── Sidebar (if used) ───────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #1c2128 !important;
    border-right: 1px solid #2d333b !important;
}

/* ── Spinner ─────────────────────────────────────────────────────── */
[data-testid="stSpinner"] { color: #26d96a !important; }

/* ── Metric (native fallback) ────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #1c2128;
    border: 1px solid #3d444d;
    border-radius: 8px;
    padding: 0.8rem 1rem;
}
[data-testid="stMetricLabel"] { color: #b0b8c4 !important; }
[data-testid="stMetricValue"] { color: #e8edf3 !important; font-variant-numeric: tabular-nums; }
[data-testid="stMetricDelta"] svg { fill: currentColor; }

/* ── Subheaders ──────────────────────────────────────────────────── */
h1 { color: #e8edf3 !important; font-size: 1.4rem !important; margin-bottom: 0.5rem !important; }
h2, h3 { color: #e8edf3 !important; }
p, li { color: #d0d8e4 !important; }
label, [data-testid="stWidgetLabel"] p { color: #c8d0dc !important; }
small, .caption { color: #b0b8c4 !important; }

/* ── Dropdown popups ─────────────────────────────────────────────── */
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
    background: #1c2128 !important;
    border-color: #3d444d !important;
}
[role="option"], [data-baseweb="menu-item"] {
    color: #e8edf3 !important;
    background: #1c2128 !important;
}
[role="option"]:hover, [data-baseweb="menu-item"]:hover {
    background: #2d333b !important;
}

/* ── Multiselect tag chips ───────────────────────────────────────── */
[data-baseweb="tag"] {
    background: #1a4731 !important;
    color: #26d96a !important;
    border-color: #26d96a !important;
}
[data-baseweb="tag"] span { color: #26d96a !important; }

/* ── Baseweb select inner container (multiselect) ────────────────── */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div {
    background: #1c2128 !important;
    border-color: #3d444d !important;
    color: #e8edf3 !important;
}
[data-baseweb="select"] input {
    background: transparent !important;
    color: #e8edf3 !important;
    caret-color: #e8edf3 !important;
}
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"],
[data-baseweb="no-result"] {
    background: #1c2128 !important;
    color: #b0b8c4 !important;
}

/* ── File uploader ───────────────────────────────────────────────── */
[data-testid="stFileUploader"] > div {
    background: #1c2128 !important;
    border-color: #3d444d !important;
    color: #e8edf3 !important;
}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span { color: #b0b8c4 !important; }

/* ── Timing card ─────────────────────────────────────────────────── */
.pt-timing-card { background: #0d1117; border-radius: 4px; padding: 8px 12px; margin: 12px 0; }
.pt-timing-label { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
.pt-timing-reason { color: #c9d1d9; font-size: 0.85rem; }

/* ── Index table ─────────────────────────────────────────────────── */
.pt-idx-th { padding: 8px 14px; text-align: left; color: #8b949e; font-size: 0.78rem; font-weight: 600; border-bottom: 2px solid #30363d; }
.pt-idx-td { padding: 8px 14px; border-bottom: 1px solid #21262d; }
</style>
"""

_LIGHT_CSS = """
<style>
/* ── Global light background ────────────────────────────────────── */
html, body, [data-testid="stApp"] {
    background-color: #f6f8fa !important;
    color: #24292f !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* ── Hide Streamlit chrome ──────────────────────────────────────── */
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ── Main content area ──────────────────────────────────────────── */
[data-testid="stAppViewContainer"] > .main > .block-container {
    padding-top: 0.5rem !important;
    max-width: 1400px;
}

/* ── Header bar ─────────────────────────────────────────────────── */
.pt-header {
    display: flex;
    align-items: center;
    padding: 0.6rem 0 0.4rem 0;
    border-bottom: 1px solid #d0d7de;
    margin-bottom: 0.25rem;
}
.pt-logo {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1a7f37;
    letter-spacing: -0.3px;
}
.pt-nav-divider {
    border-bottom: 1px solid #d0d7de;
    margin: 0.3rem 0 0.8rem 0;
}

/* ── Navigation buttons ─────────────────────────────────────────── */
[data-testid="stButton"] button {
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.35rem 0.5rem !important;
    transition: all 0.15s ease !important;
}
[data-testid="stButton"] button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #d0d7de !important;
    color: #57606a !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
    background: #f3f4f6 !important;
    border-color: #1a7f37 !important;
    color: #24292f !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: #1a7f37 !important;
    border: 1px solid #1a7f37 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background: #166c30 !important;
}

/* ── Cards ──────────────────────────────────────────────────────── */
.pt-card {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
}
.pt-card-label {
    font-size: 0.72rem;
    color: #57606a;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 0.2rem;
}
.pt-card-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #24292f;
    font-variant-numeric: tabular-nums;
    line-height: 1.2;
}
.pt-card-delta-pos {
    font-size: 0.85rem;
    color: #1a7f37;
    font-weight: 600;
}
.pt-card-delta-neg {
    font-size: 0.85rem;
    color: #cf222e;
    font-weight: 600;
}
.pt-card-delta-neutral {
    font-size: 0.85rem;
    color: #57606a;
    font-weight: 600;
}

/* ── Direction badges ───────────────────────────────────────────── */
.badge-buy {
    background: #dafbe1; color: #1a7f37;
    padding: 3px 10px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 700;
    border: 1px solid #1a7f37;
}
.badge-sell {
    background: #ffebe9; color: #cf222e;
    padding: 3px 10px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 700;
    border: 1px solid #cf222e;
}
.badge-hold {
    background: #f6f8fa; color: #57606a;
    padding: 3px 10px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 700;
    border: 1px solid #8c959f;
}

/* ── Inputs, selects ────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
    background: #ffffff !important;
    border-color: #d0d7de !important;
    color: #24292f !important;
    border-radius: 6px !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important;
    border-color: #d0d7de !important;
    color: #24292f !important;
}
[data-testid="stMultiSelect"] > div > div {
    background: #ffffff !important;
    border-color: #d0d7de !important;
    color: #24292f !important;
}
[data-testid="stTextArea"] textarea {
    background: #ffffff !important;
    border-color: #d0d7de !important;
    color: #24292f !important;
}

/* ── Sliders ─────────────────────────────────────────────────────── */
[data-testid="stSlider"] > div > div > div > div {
    background: #1a7f37 !important;
}

/* ── DataFrames ─────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #d0d7de !important;
    border-radius: 8px !important;
    overflow: hidden;
}
.dvn-scroller { background: #ffffff !important; }

/* ── Inline HTML tables (trade log) ─────────────────────────────── */
table.dataframe { width:100%; border-collapse:collapse; font-size:0.84rem; }
table.dataframe thead tr th {
    padding:6px 10px; text-align:left !important;
    border-bottom:2px solid #d0d7de;
    color:#57606a; font-size:0.74rem;
    text-transform:uppercase; letter-spacing:0.5px; font-weight:600;
}
table.dataframe tbody tr td { padding:5px 10px; border-bottom:1px solid #eaecef; color:#24292f; }
table.dataframe tbody tr:hover td { background:#f6f8fa; }

/* ── Expanders ──────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #d0d7de !important;
    border-radius: 8px !important;
}

/* ── Dividers ───────────────────────────────────────────────────── */
hr { border-color: #d0d7de !important; }

/* ── Alerts / info boxes ─────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
}

/* ── Tab styling ─────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tab"] {
    color: #57606a !important;
    font-weight: 500;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #1a7f37 !important;
    border-bottom-color: #1a7f37 !important;
}

/* ── Sidebar (if used) ───────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #d0d7de !important;
}

/* ── Spinner ─────────────────────────────────────────────────────── */
[data-testid="stSpinner"] { color: #1a7f37 !important; }

/* ── Metric (native fallback) ────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 0.8rem 1rem;
}
[data-testid="stMetricLabel"] { color: #57606a !important; }
[data-testid="stMetricValue"] { color: #24292f !important; font-variant-numeric: tabular-nums; }
[data-testid="stMetricDelta"] svg { fill: currentColor; }

/* ── Subheaders ──────────────────────────────────────────────────── */
h1 { color: #24292f !important; font-size: 1.4rem !important; margin-bottom: 0.5rem !important; }
h2, h3 { color: #24292f !important; }
p, li { color: #24292f !important; }
label, [data-testid="stWidgetLabel"] p { color: #57606a !important; }
small, .caption { color: #8c959f !important; }

/* ── Dropdown popups ─────────────────────────────────────────────── */
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
    background: #ffffff !important;
    border-color: #d0d7de !important;
}
[role="option"], [data-baseweb="menu-item"] {
    color: #24292f !important;
    background: #ffffff !important;
}
[role="option"]:hover, [data-baseweb="menu-item"]:hover {
    background: #f6f8fa !important;
}

/* ── Multiselect tag chips ───────────────────────────────────────── */
[data-baseweb="tag"] {
    background: #dafbe1 !important;
    color: #1a7f37 !important;
    border-color: #1a7f37 !important;
}
[data-baseweb="tag"] span { color: #1a7f37 !important; }

/* ── Baseweb select inner container (multiselect) ────────────────── */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div {
    background: #ffffff !important;
    border-color: #d0d7de !important;
    color: #24292f !important;
}
[data-baseweb="select"] input {
    background: transparent !important;
    color: #24292f !important;
    caret-color: #24292f !important;
}
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"],
[data-baseweb="no-result"] {
    background: #ffffff !important;
    color: #57606a !important;
}

/* ── File uploader ───────────────────────────────────────────────── */
[data-testid="stFileUploader"] > div {
    background: #ffffff !important;
    border-color: #d0d7de !important;
    color: #24292f !important;
}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span { color: #57606a !important; }

/* ── Timing card ─────────────────────────────────────────────────── */
.pt-timing-card { background: #f6f8fa; border-radius: 4px; padding: 8px 12px; margin: 12px 0; }
.pt-timing-label { font-size: 0.75rem; color: #57606a; text-transform: uppercase; letter-spacing: 1px; }
.pt-timing-reason { color: #24292f; font-size: 0.85rem; }

/* ── Index table ─────────────────────────────────────────────────── */
.pt-idx-th { padding: 8px 14px; text-align: left; color: #57606a; font-size: 0.78rem; font-weight: 600; border-bottom: 2px solid #d0d7de; }
.pt-idx-td { padding: 8px 14px; border-bottom: 1px solid #eaecef; }
</style>
"""


def inject_theme(dark: bool = False) -> None:
    st.markdown(_DARK_CSS if dark else _LIGHT_CSS, unsafe_allow_html=True)


def inject_dark_theme() -> None:
    inject_theme(dark=True)
