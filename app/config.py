from pathlib import Path

APP_NAME = "bTest — BTCUSDT Liquidity Grab"
SYMBOL = "BTCUSDT"
WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@bookTicker"
MAX_BUFFER = 1000
STALE_MS = 3000
LOG_THROTTLE_MS = 1500

FAST_WINDOW_MS = 10_000
MID_WINDOW_MS = 30_000
SLOW_WINDOW_MS = 120_000
MIN_TICKS_FAST = 5
MAX_ALLOWED_SPREAD_PCT = 0.03
STALE_AFTER_MS = 3000
ANALYSIS_LOG_INTERVAL_MS = 2000

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
LOG_FILE = LOG_DIR / "app.log"
