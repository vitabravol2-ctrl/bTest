from pathlib import Path

APP_NAME = "bTest — BTCUSDT Liquidity Grab"
SYMBOL = "BTCUSDT"
WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@bookTicker"
MAX_BUFFER = 1000
STALE_MS = 3000
LOG_THROTTLE_MS = 1500

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
LOG_FILE = LOG_DIR / "app.log"
