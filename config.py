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
MIN_NET_PROFIT_THRESHOLD = float(os.getenv("MIN_NET_PROFIT_THRESHOLD", "0.3"))  # мінімальний % чистого прибутку після комісій
BUY_FEE_TYPE = os.getenv("BUY_FEE_TYPE", "taker").lower()  # Тип комісії для купівлі
SELL_FEE_TYPE = os.getenv("SELL_FEE_TYPE", "taker").lower()  # Тип комісії для продажу

# Інтервали перевірки
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))  # звичайний інтервал перевірки в секундах
PEAK_CHECK_INTERVAL = int(os.getenv("PEAK_CHECK_INTERVAL", "30"))  # інтервал під час пікових годин

# Оптимальні часові вікна для арбітражу (UTC)
PEAK_HOURS = [
    (13, 16),  # Перетин американської та європейської сесій
    (1, 4),    # Азійська торгова сесія
    (12, 13),  # Перехідний період 1
    (0, 1)     # Перехідний період 2
]

# Розширений список криптовалют для арбітражу
PAIRS = [
    # Основні пари
    "BTC/USDT", 
    "ETH/USDT", 
    "XRP/USDT",
    "BNB/USDT",
    "SOL/USDT",
    # Додаткові пари з високим потенціалом арбітражу
    "TRX/USDT",  # Найнижчі комісії
    "ADA/USDT",  # Хороші різниці KuCoin-Kraken
    "HBAR/USDT", # Високі різниці KuCoin-Binance
    "NEAR/USDT", # Високі різниці KuCoin-Kraken
    "ATOM/USDT", # Хороші різниці Binance-Kraken
    "MATIC/USDT" # Корисно для трикутного арбітражу
]

# Налаштування розміру ордерів
ORDER_SIZES = {
    "BTC/USDT": 0.01,    # ~500 USD
    "ETH/USDT": 0.1,     # ~300 USD
    "DEFAULT": 100       # 100 USDT для інших пар
}

# Налаштування мереж для транзакцій
NETWORK_PREFERENCES = {
    "USDT": ["TRC20", "BEP20", "SOL", "ERC20"],  # В порядку пріоритету
    "USDC": ["BEP20", "SOL", "TRC20", "ERC20"],
    "DEFAULT": "TRC20"  # За замовчуванням
}

# Налаштування трикутного арбітражу
TRIANGULAR_PATHS = [
    ["USDT", "MATIC", "BTC", "USDT"],
    ["USDT", "XRP", "BTC", "USDT"],
    ["USDT", "SOL", "ETH", "USDT"],
    ["USDT", "TRX", "BTC", "USDT"]
]

# Налаштування комісій
EXCHANGE_FEES = {
    "binance": {
        "maker": float(os.getenv("BINANCE_MAKER_FEE", "0.1")),
        "taker": float(os.getenv("BINANCE_TAKER_FEE", "0.1")),
        "withdrawal": {  # Комісії за виведення
            "BTC": 0.0005,
            "ETH": 0.005,
            "XRP": 0.2,
            "TRX": 1,
            "SOL": 0.01,
            "USDT": 1,
            "DEFAULT": 0.1
        },
        "discount_token": "BNB",
        "discount_percent": float(os.getenv("BINANCE_DISCOUNT_PERCENT", "25"))
    },
    "kucoin": {
        "maker": float(os.getenv("KUCOIN_MAKER_FEE", "0.1")),
        "taker": float(os.getenv("KUCOIN_TAKER_FEE", "0.1")),
        "withdrawal": {
            "BTC": 0.0005,
            "ETH": 0.004,
            "XRP": 1,
            "TRX": 5,
            "SOL": 0.01,
            "USDT": 1,
            "DEFAULT": 0.1
        },
        "discount_token": "KCS",
        "discount_percent": float(os.getenv("KUCOIN_DISCOUNT_PERCENT", "20"))
    },
    "kraken": {
        "maker": float(os.getenv("KRAKEN_MAKER_FEE", "0.16")),
        "taker": float(os.getenv("KRAKEN_TAKER_FEE", "0.26")),
        "withdrawal": {
            "BTC": 0.0005,
            "ETH": 0.005,
            "XRP": 0.02,
            "TRX": 1,
            "SOL": 0.01,
            "USDT": 2.5,
            "DEFAULT": 0.1
        },
        "discount_token": None,
        "discount_percent": 0
    }
}

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAIN_LOG_FILE = "logs/main.log"
TELEGRAM_LOG_FILE = "logs/telegram.log"
ARBITRAGE_LOG_FILE = "logs/arbitrage.log"
TRIANGULAR_LOG_FILE = "logs/triangular.log"

# Exchange API settings
REQUEST_TIMEOUT = 10  # seconds
RATE_LIMIT_RETRY = True

# Web-server settings
WEB_SERVER_ENABLED = bool(int(os.getenv("WEB_SERVER_ENABLED", "0")))
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", "8080")))
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "localhost")

# App settings
APP_NAME = "Bitmonbot"
START_MESSAGE = f"✅ {APP_NAME} стартував!"
VERSION = "0.3.0"

# Налаштування прослизання
MAX_ACCEPTABLE_SLIPPAGE = float(os.getenv("MAX_ACCEPTABLE_SLIPPAGE", "1.0"))  # максимальне прийнятне прослизання у відсотках
