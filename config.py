# config.py
import os
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()

# App settings
APP_NAME = "Bitmonbot"
VERSION = "0.2.1"  # Додано на основі інформації з Changelog
START_MESSAGE = f"✅ {APP_NAME} стартував!"

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

# Комісії бірж відповідно до реальних тарифів
EXCHANGE_FEES = {
    'binance': {
        'maker': float(os.getenv("BINANCE_MAKER_FEE", "0.1")),  # 0.1%
        'taker': float(os.getenv("BINANCE_TAKER_FEE", "0.1"))   # 0.1%
    },
    'kucoin': {
        'maker': float(os.getenv("KUCOIN_MAKER_FEE", "0.1")),   # 0.1%
        'taker': float(os.getenv("KUCOIN_TAKER_FEE", "0.1"))    # 0.1%
    },
    'kraken': {
        'maker': float(os.getenv("KRAKEN_MAKER_FEE", "0.25")),  # 0.25%
        'taker': float(os.getenv("KRAKEN_TAKER_FEE", "0.40"))   # 0.40%
    }
}

# Використовувати maker чи taker комісії для розрахунків
# Окремо для купівлі і продажу
BUY_FEE_TYPE = os.getenv("BUY_FEE_TYPE", "taker").lower()  # Тип комісії для купівлі
SELL_FEE_TYPE = os.getenv("SELL_FEE_TYPE", "taker").lower()  # Тип комісії для продажу

# Враховувати комісії при розрахунку прибутку
INCLUDE_FEES = os.getenv("INCLUDE_FEES", "True").lower() == "true"

# Supported cryptocurrency pairs
PAIRS = [
    "BTC/USDT", 
    "ETH/USDT", 
    "XRP/USDT",
    "BNB/USDT",
    "SOL/USDT",
    # Додаємо пари з аналізу ринку, які були визначені як найбільш перспективні в документації
    "TRX/USDT",
    "HBAR/USDT",
    "NEAR/USDT",
    "ATOM/USDT",
    "ADA/USDT",
    "AVAX/USDT"
]

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAIN_LOG_FILE = "logs/main.log"
TELEGRAM_LOG_FILE = "logs/telegram.log"
ARBITRAGE_LOG_FILE = "logs/arbitrage.log"

# Exchange API settings
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))  # seconds
RATE_LIMIT_RETRY = os.getenv("RATE_LIMIT_RETRY", "True").lower() == "true"

# Web server settings
WEB_SERVER_ENABLED = os.getenv("WEB_SERVER_ENABLED", "False").lower() == "true"
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "localhost")
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", "8080"))

# HTTP Session settings
HTTP_SESSION_TIMEOUT = int(os.getenv("HTTP_SESSION_TIMEOUT", "30"))  # seconds
HTTP_SESSION_RETRY_COUNT = int(os.getenv("HTTP_SESSION_RETRY_COUNT", "3"))
HTTP_SESSION_RETRY_DELAY = int(os.getenv("HTTP_SESSION_RETRY_DELAY", "2"))  # seconds

# Performance Settings
TICKERS_BATCH_SIZE = int(os.getenv("TICKERS_BATCH_SIZE", "5"))  # How many tickers to process in one batch
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))  # Max concurrent API requests

# Status Updates
SAVE_STATUS_INTERVAL = int(os.getenv("SAVE_STATUS_INTERVAL", "300"))  # seconds (5 min)
TELEGRAM_STATUS_INTERVAL = int(os.getenv("TELEGRAM_STATUS_INTERVAL", "3600"))  # seconds (1 hour)
