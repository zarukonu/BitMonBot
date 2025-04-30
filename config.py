import os
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()

# API keys
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY", "")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET", "")
KUCOIN_API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE", "")
KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY", "")
KRAKEN_API_SECRET = os.getenv("KRAKEN_API_SECRET", "")

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Arbitrage settings
MIN_PROFIT_THRESHOLD = float(os.getenv("MIN_PROFIT_THRESHOLD", "0.5"))  # мінімальний % прибутку
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))  # інтервал перевірки в секундах

# Supported cryptocurrency pairs
PAIRS = [
    "BTC/USDT", 
    "ETH/USDT", 
    "XRP/USDT",
    "BNB/USDT",
    "SOL/USDT"
]

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAIN_LOG_FILE = "logs/main.log"
TELEGRAM_LOG_FILE = "logs/telegram.log"
ARBITRAGE_LOG_FILE = "logs/arbitrage.log"

# Exchange API settings
REQUEST_TIMEOUT = 10  # seconds
RATE_LIMIT_RETRY = True

# App settings
APP_NAME = "Bitmonbot"
START_MESSAGE = f"✅ {APP_NAME} стартував!"
