# config.py
import os
import json
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

# Шлях до файлу з користувачами
USERS_FILE = os.getenv("USERS_FILE", "users.json")

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
# Список всіх підтримуваних пар
ALL_PAIRS = [
    "BTC/USDT", 
    "ETH/USDT", 
    "XRP/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "ADA/USDT",
    "DOT/USDT",
    "DOGE/USDT",
    "AVAX/USDT",
    "MATIC/USDT",
    "LTC/USDT",
    "UNI/USDT",
    "LINK/USDT",
    "ATOM/USDT",
    "XLM/USDT",
    "FIL/USDT"
]

# Specifičnі pary dlja kožnoji birži
EXCHANGE_SPECIFIC_PAIRS = {
    'binance': ALL_PAIRS,
    'kucoin': ALL_PAIRS,
    'kraken': [
        "BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT",
        "ADA/USDT", "DOT/USDT", "DOGE/USDT", "AVAX/USDT", "MATIC/USDT",
        "LTC/USDT", "UNI/USDT", "LINK/USDT", "ATOM/USDT",
        "XLM/USDT", "FIL/USDT"
        # Прибрано: "TRX/USDT", "HBAR/USDT", "NEAR/USDT", "BNB/USDT", "VET/USDT", "THETA/USDT"
    ]
}

# Список усіх підтримуваних пар для використання в системі
PAIRS = ALL_PAIRS

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAIN_LOG_FILE = "logs/main.log"
TELEGRAM_LOG_FILE = "logs/telegram.log"
ARBITRAGE_LOG_FILE = "logs/arbitrage.log"
USERS_LOG_FILE = "logs/users.log"

# Exchange API settings
REQUEST_TIMEOUT = 10  # seconds
RATE_LIMIT_RETRY = True

# App settings
APP_NAME = "Bitmonbot"
VERSION = "1.0.0"
START_MESSAGE = f"✅ {APP_NAME} стартував!"

# Налаштування для роботи з користувачами
ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "").split(",")  # ID адміністраторів через кому
DEFAULT_MIN_PROFIT = 0.8  # Мінімальний поріг прибутку для нових користувачів

# Команди бота
BOT_COMMANDS = {
    "/start": "Почати роботу з ботом",
    "/help": "Показати довідку",
    "/status": "Перевірити статус доступу",
    "/approve": "Схвалити користувача (тільки для адміністраторів)",
    "/block": "Заблокувати користувача (тільки для адміністраторів)",
    "/users": "Список користувачів (тільки для адміністраторів)",
    "/pairs": "Керування валютними парами",
    "/threshold": "Встановити мінімальний поріг прибутку",
    "/settings": "Налаштування користувача"
}

def load_users():
    """
    Завантажує список користувачів з файлу
    """
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Помилка при завантаженні користувачів: {e}")
        return {}

def save_users(users):
    """
    Зберігає список користувачів у файл
    """
    try:
        # Створюємо директорію, якщо вона не існує
        users_dir = os.path.dirname(USERS_FILE)
        if users_dir and not os.path.exists(users_dir):
            os.makedirs(users_dir)
            
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=4)
        return True
    except Exception as e:
        print(f"Помилка при збереженні користувачів: {e}")
        return False
