"""
Configuration constants for the Stock Tracker.
"""

# ─── Scoring Weights ───────────────────────────────────────────────
FUNDAMENTAL_WEIGHT = 0.40
TECHNICAL_WEIGHT = 0.35
EVENT_WEIGHT = 0.25

# ─── Score Tier Thresholds ─────────────────────────────────────────
TIER_STRONG_BUY = 75
TIER_BUY = 60
TIER_WATCH = 45
# Below TIER_WATCH → "avoid"

# ─── Fundamental Thresholds ────────────────────────────────────────
IDEAL_PE_MAX = 40          # PE above this is expensive
IDEAL_PB_MAX = 5           # PB above this is expensive
IDEAL_ROE_MIN = 12         # ROE above this is good (%)
IDEAL_REVENUE_GROWTH = 10  # QoQ revenue growth target (%)
IDEAL_PROFIT_GROWTH = 12   # QoQ profit growth target (%)
IDEAL_DEBT_EQUITY_MAX = 1.0  # D/E below this is healthy
IDEAL_CURRENT_RATIO_MIN = 1.2  # Current ratio above this is healthy
IDEAL_PROMOTER_HOLDING = 50  # Promoter holding above this is good (%)

# ─── Technical Parameters ──────────────────────────────────────────
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_SWEET_SPOT = (40, 65)  # Ideal range for growth stocks

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

SMA_SHORT = 50
SMA_LONG = 200
EMA_PERIOD = 20

BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

ADX_PERIOD = 14
ADX_STRONG_TREND = 25

# ─── Data Fetching ─────────────────────────────────────────────────
FETCH_DELAY_SECONDS = 0.3      # Delay between yfinance calls
HISTORY_PERIOD = "1y"          # 1 year of price history
MAX_RETRIES = 2                # Retries on fetch failure

# ─── Output ────────────────────────────────────────────────────────
OUTPUT_DIR = "docs/data"
OUTPUT_FILE = "docs/data/results.json"
