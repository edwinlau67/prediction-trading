# API Reference

All public classes and methods in `src/`. Import via `from src import PredictionTradingSystem` or individual modules.

---

## `PredictionTradingSystem` — `src/system.py`

Top-level façade. Instantiate once per ticker per session.

```python
class PredictionTradingSystem:
    def __init__(
        self,
        ticker: str,
        *,
        initial_capital: float | None = None,   # overrides config portfolio.initial_capital
        config_path: str | Path | None = None,  # path to YAML; default: config/default.yaml
        enable_ai: bool | None = None,           # overrides config ai.enabled
        api_key: str | None = None,              # Anthropic key; default: $ANTHROPIC_API_KEY
        out_root: str | Path = "results",        # where run dirs are written
    ) -> None

    def fetch(
        self,
        *,
        lookback_days: int | None = None,   # default: config data.lookback_days (365)
        start: str | None = None,           # ISO date "YYYY-MM-DD"; use with end=
        end: str | None = None,
    ) -> MarketData

    def predict(
        self,
        market: MarketData | None = None,
        *,
        hourly_4h: pd.DataFrame | None = None,  # 4H-resampled enriched OHLCV for confluence
    ) -> Prediction
        # Runs TechnicalIndicators.compute_all, weekly resampling, and UnifiedPredictor.

    def backtest(self, start: str, end: str) -> BacktestResult
        # Fetches history, runs Backtester, stores MarketData for later save_report.

    def save_report(
        self,
        *,
        result: BacktestResult | None = None,
        prediction: Prediction | None = None,
    ) -> Path
        # Writes markdown + PNG charts to results/<prefix>_<timestamp>/. Returns run dir.

    def build_auto_trader(
        self,
        tickers: list[str] | tuple[str, ...] | None = None,
        *,
        broker: BaseBroker | None = None,
        portfolio: Portfolio | None = None,
        state_path: str | Path | None = None,
        trade_log_path: str | Path | None = None,
        dry_run: bool = False,
        enforce_market_hours: bool | None = None,
        log_dir: str | Path | None = None,
        lookback_days: int | None = None,
    ) -> AutoTrader
```

---

## `WatchlistScanner` — `src/scanner.py`

Parallel rule-based screening without charts or AI.

```python
@dataclass
class ScanResult:
    ticker: str
    direction: Direction          # "bullish" | "bearish" | "neutral"
    confidence: float             # 0..1
    top_factors: list[str]        # human-readable factor names
    current_price: float | None
    error: str | None

class WatchlistScanner:
    def __init__(
        self,
        *,
        categories: tuple[str, ...] | None = None,  # default: all 6 categories
        lookback_days: int = 365,
        min_confidence: float = 0.0,
        workers: int = 4,
    ) -> None

    def scan(self, tickers: list[str]) -> list[ScanResult]
        # Returns results sorted by confidence descending. Errors are captured per-ticker.
```

---

## `SignalScorer` — `src/prediction/signal_scorer.py`

Point-based rule engine. Stateless; call `score()` with any enriched DataFrame.

```python
@dataclass
class ScoredSignal:
    direction: Direction
    confidence: float
    factors: list[Factor]
    category_points: dict[str, int]   # net points per category
    components: dict[str, float]      # legacy 5-component view (backtester compat)
    net_points: int
    abs_points: int
    bullish_factors: list[Factor]     # property
    bearish_factors: list[Factor]     # property

class SignalScorer:
    def __init__(
        self,
        *,
        categories: Iterable[str] | None = None,   # default: all 6
        multi_timeframe_bonus: int = 2,
        confidence_scale: float = 10.0,
        weights: dict[str, float] | None = None,   # legacy; kept for API compat
    ) -> None

    def score(
        self,
        df: pd.DataFrame,            # daily OHLCV enriched by TechnicalIndicators.compute_all()
        *,
        weekly: pd.DataFrame | None = None,     # weekly resampled + enriched (for confluence)
        hourly_4h: pd.DataFrame | None = None,  # 4H enriched (for confluence); new in v1.1
        fundamentals: dict | None = None,       # yfinance fundamentals dict
    ) -> ScoredSignal
```

**Indicator categories:**

| Category | Rules fired |
|---|---|
| `trend` | Price vs SMA50/200, Golden/Death Cross, MACD crossover, EMA12 vs EMA26 |
| `momentum` | RSI bands (30/70), RSI midline (50), Stochastic cross, Stochastic bands |
| `volatility` | Bollinger Band touches, ATR regime (elevated/calm) |
| `volume` | OBV trend, Volume spike direction |
| `support` | Price vs Pivot Point, Trendline hold/break |
| `fundamental` | P/E, PEG, Revenue growth, Earnings growth, Net margin, ROE, D/E, Current ratio, P/B |

---

## `AIPredictor` — `src/prediction/ai_predictor.py`

Claude tool-use prediction. Requires `ANTHROPIC_API_KEY`.

```python
@dataclass
class AIPrediction:
    ticker: str
    timeframe: str
    direction: Direction
    confidence: float
    current_price: float
    price_target: float
    target_date: str
    risk_level: str            # "low" | "medium" | "high"
    key_factors: list[str]
    fundamentals: dict
    narrative: str             # human-readable analysis

class AIPredictor:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2000,
        data_fetcher: DataFetcher | None = None,
        categories: tuple[str, ...] | None = None,
    ) -> None

    def predict(self, ticker: str, timeframe: str = "1w") -> AIPrediction
```

---

## `UnifiedPredictor` — `src/prediction/predictor.py`

Fuses rule-based and AI signals.

```python
@dataclass
class Prediction:
    ticker: str
    direction: Direction
    confidence: float
    current_price: float
    price_target: float | None
    target_date: str | None
    risk_level: str
    rule_signal: ScoredSignal | None
    ai_signal: AIPrediction | None
    factors: list[Factor]
    meta: dict

class UnifiedPredictor:
    def __init__(
        self,
        scorer: SignalScorer | None = None,
        ai: AIPredictor | None = None,
        ai_enabled: bool = False,
        ai_weight: float = 0.5,       # 0=rule-only, 1=AI-only
        min_confidence: float = 0.40,
        timeframe: str = "1w",
    ) -> None

    def predict(
        self,
        ticker: str,
        df: pd.DataFrame,
        *,
        current_price: float,
        weekly: pd.DataFrame | None = None,
        hourly_4h: pd.DataFrame | None = None,
        fundamentals: dict | None = None,
    ) -> Prediction
```

**Fusion formula:** `blended = (1 - ai_weight) × rule_signed + ai_weight × ai_signed`  
`rule_signed` and `ai_signed` are confidence values in `[-1, +1]`. Direction flips at `|blended| > 0.05`.

---

## `TechnicalIndicators` — `src/indicators/technical.py`

All methods are `@staticmethod` or `@classmethod`. All inputs/outputs are `pd.Series` or `pd.DataFrame`.

```python
class TechnicalIndicators:
    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series

    @staticmethod
    def macd(
        close: pd.Series,
        fast: int = 12, slow: int = 26, signal: int = 9,
    ) -> tuple[pd.Series, pd.Series, pd.Series]   # macd, signal_line, histogram

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series

    @staticmethod
    def stochastic(
        high: pd.Series, low: pd.Series, close: pd.Series,
        k_period: int = 14, d_period: int = 3,
    ) -> tuple[pd.Series, pd.Series]   # %K, %D

    @staticmethod
    def bollinger(
        close: pd.Series, period: int = 20, num_std: float = 2.0,
    ) -> tuple[pd.Series, pd.Series, pd.Series]   # upper, middle, lower

    @staticmethod
    def atr(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14,
    ) -> pd.Series

    @staticmethod
    def adx(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14,
    ) -> tuple[pd.Series, pd.Series, pd.Series]   # adx, +DI, -DI

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series

    @classmethod
    def compute_all(cls, ohlcv: pd.DataFrame) -> pd.DataFrame
        # Adds columns: SMA20, SMA50, SMA200, EMA12, EMA20, EMA26,
        # MACD, MACD_signal, MACD_hist, RSI, Stoch_K, Stoch_D,
        # BB_upper, BB_middle, BB_lower, ATR, ADX, OBV, VolumeSpike
```

---

## `SupportResistance` — `src/indicators/levels.py`

```python
@dataclass
class PivotLevels:
    pp: float    # pivot point
    r1: float; r2: float    # resistance
    s1: float; s2: float    # support

class SupportResistance:
    @staticmethod
    def pivot_points(high: float, low: float, close: float) -> PivotLevels

    @staticmethod
    def fibonacci(
        ohlcv: pd.DataFrame, lookback: int = 126,
    ) -> dict[str, float]   # keys: "high", "low", "0.236", "0.382", "0.5", "0.618", "0.786"

    @staticmethod
    def trendlines(
        df: pd.DataFrame, window: int = 5,
    ) -> dict[str, tuple[float, float]]   # "support"/"resistance" → (slope, intercept)
```

---

## `RiskManager` — `src/trading/risk_manager.py`

```python
@dataclass
class TradeProposal:
    ticker: str
    side: Side                # "long" | "short"
    quantity: int
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_per_share: float
    risk_reward: float
    rationale: str

class RiskManager:
    def __init__(
        self,
        max_positions: int = 5,
        max_position_size_pct: float = 0.05,
        max_daily_loss_pct: float = 0.02,
        min_risk_reward: float = 1.5,
        stop_loss_atr_mult: float = 2.0,
        take_profit_atr_mult: float = 3.0,
        min_confidence: float = 0.40,
    ) -> None

    def evaluate(
        self,
        prediction: Prediction,
        portfolio: Portfolio,
        atr: float,
        timestamp: datetime,
    ) -> TradeProposal | None
        # Returns None if any gate fails. Gates checked in order:
        # 1. min_confidence  2. max_positions  3. position sizing
        # 4. available cash  5. daily loss cap  6. R:R ratio
```

---

## `Portfolio` — `src/trading/portfolio.py`

```python
@dataclass
class Position:
    ticker: str
    side: Side
    quantity: int
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float

    def unrealised(self, current_price: float) -> float
    def should_exit(self, current_price: float) -> tuple[bool, str]
        # Returns (True, reason) when stop or target is hit.

@dataclass
class Trade:
    ticker: str; side: Side; quantity: int
    entry_price: float; exit_price: float
    entry_time: datetime; exit_time: datetime
    pnl: float; reason: str
    return_pct: float    # property
    is_win: bool         # property

@dataclass
class Portfolio:
    initial_capital: float = 10_000.0
    commission_per_trade: float = 1.0
    cash: float                       # post-init = initial_capital
    positions: dict[str, Position]
    closed_trades: list[Trade]
    equity_curve: list[tuple[datetime, float]]

    def equity(self, prices: dict[str, float]) -> float
        # cash + sum of mark-to-market position values

    def mark(self, timestamp: datetime, prices: dict[str, float]) -> None
        # Appends an equity_curve snapshot.

    def open(self, position: Position) -> None
        # Deducts cash, adds position. Raises ValueError if insufficient cash.

    def close(
        self, ticker: str, price: float, when: datetime, reason: str,
    ) -> Trade
        # Realises P&L, restores cash, removes position, appends Trade.
```

---

## `AutoTrader` — `src/trading/auto_trader.py`

```python
@dataclass
class TickerAction:
    ticker: str
    action: str      # "open", "close", "skip", "error"
    direction: str
    confidence: float
    detail: str

@dataclass
class CycleReport:
    started_at: datetime
    finished_at: datetime
    actions: list[TickerAction]
    equity: float
    cash: float
    errors: list[str]

class AutoTrader:
    def run_once(
        self,
        *,
        now: datetime | None = None,
    ) -> CycleReport
        # Execute one full cycle across all tickers. Returns a single CycleReport.

    def run(
        self,
        *,
        interval_seconds: int = 300,
        max_cycles: int | None = None,
    ) -> list[CycleReport]
        # Blocking loop: calls run_once(), sleeps interval_seconds, repeats until
        # max_cycles is reached or the process is interrupted. Use in a daemon thread.
```

---

## `Backtester` — `src/backtest/backtester.py`

```python
@dataclass
class BacktestResult:
    ticker: str
    start: str; end: str
    portfolio: Portfolio

    def summary(self) -> dict
        # Keys: return_pct, max_drawdown_pct, win_rate_pct, profit_factor,
        #       total_trades, winning_trades, losing_trades, avg_win_pct, avg_loss_pct

class Backtester:
    def __init__(
        self,
        predictor: UnifiedPredictor,
        risk: RiskManager,
        warmup_bars: int = 200,
    ) -> None

    def run(
        self,
        ticker: str,
        ohlcv: pd.DataFrame,
        initial_capital: float = 10_000.0,
        commission_per_trade: float = 1.0,
    ) -> BacktestResult
```

---

## `DataFetcher` — `src/data_fetcher.py`

```python
@dataclass
class MarketData:
    ticker: str
    ohlcv: pd.DataFrame          # columns: Open, High, Low, Close, Volume
    current_price: float
    fundamentals: dict
    interval: str = "1d"
    as_of: pd.Timestamp          # property: last bar timestamp

class DataFetcher:
    def __init__(self, interval: str = "1d") -> None

    def fetch_history(
        self,
        ticker: str,
        start: str | None = None,
        end: str | None = None,
        lookback_days: int = 365,
    ) -> pd.DataFrame

    def fetch_fundamentals(self, ticker: str) -> dict

    def fetch(
        self,
        ticker: str,
        lookback_days: int = 365,
        include_fundamentals: bool = True,
    ) -> MarketData
```

---

## `Factor` — `src/prediction/factor.py`

```python
Direction = Literal["bullish", "bearish", "neutral"]
IndicatorCategory = Literal["trend", "momentum", "volatility", "volume", "support", "fundamental"]
ALL_CATEGORIES: tuple[IndicatorCategory, ...] = (
    "trend", "momentum", "volatility", "volume", "support", "fundamental"
)

@dataclass
class Factor:
    category: IndicatorCategory
    name: str
    direction: Direction
    points: int         # always positive; sign is encoded in direction
    detail: str = ""

    signed: int      # property: +points if bullish, -points if bearish, 0 if neutral
    label: str       # property: "↑ name" or "↓ name"
```

---

## `StateStore` — `src/trading/state.py`

```python
class StateStore:
    def __init__(self, path: str | Path) -> None

    def load_or_create(
        self,
        initial_capital: float,
        commission_per_trade: float = 1.0,
    ) -> Portfolio

    def save(self, portfolio: Portfolio) -> None
```

---

## `BaseBroker` — `src/trading/broker.py`

Implement these three methods to integrate a live broker:

```python
class BaseBroker(ABC):
    @abstractmethod
    def get_quote(self, ticker: str) -> float

    @abstractmethod
    def place_order(self, order: Order) -> Fill | None

    @abstractmethod
    def close_position(
        self,
        ticker: str,
        reason: str,
        quote: float | None = None,
        when: datetime | None = None,
    ) -> Trade | None
```
