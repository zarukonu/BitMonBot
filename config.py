# Supported cryptocurrency pairs
# Список найбільш ліквідних і надійних пар, які підтримуються всіма біржами
ALL_PAIRS = [
    "BTC/USDT", 
    "ETH/USDT", 
    "XRP/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "ADA/USDT",
    "DOT/USDT",
    "DOGE/USDT",
    "MATIC/USDT",
    "LTC/USDT",
    "LINK/USDT",
    "ATOM/USDT",
    "XLM/USDT"
]

# Специфічні пари для кожної біржі з урахуванням їх особливостей
EXCHANGE_SPECIFIC_PAIRS = {
    'binance': [
        "BTC/USDT", "ETH/USDT", "XRP/USDT", "BNB/USDT", "SOL/USDT",
        "ADA/USDT", "DOT/USDT", "DOGE/USDT", "MATIC/USDT", "LTC/USDT", 
        "LINK/USDT", "ATOM/USDT", "XLM/USDT", "AVAX/USDT", "UNI/USDT", 
        "ALGO/USDT", "NEAR/USDT", "FIL/USDT"
    ],
    'kucoin': [
        "BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT",
        "ADA/USDT", "DOT/USDT", "DOGE/USDT", "MATIC/USDT", "LTC/USDT", 
        "LINK/USDT", "ATOM/USDT", "XLM/USDT", "AVAX/USDT", "UNI/USDT"
    ],
    'kraken': [
        "BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT",
        "ADA/USDT", "DOT/USDT", "DOGE/USDT", "MATIC/USDT", "LTC/USDT", 
        "LINK/USDT", "ATOM/USDT", "XLM/USDT"
    ]
}

# Пари для трикутного арбітражу, які гарантовано мають достатню ліквідність
TRIANGULAR_PATHS = [
    ["USDT", "BTC", "ETH", "USDT"],
    ["USDT", "BTC", "SOL", "USDT"],
    ["USDT", "ETH", "SOL", "USDT"],
    ["USDT", "BTC", "XRP", "USDT"],
    ["USDT", "ETH", "LINK", "USDT"],
    ["USDT", "ETH", "MATIC", "USDT"]
]

# Список пар, які будуть використовуватися за замовчуванням
PAIRS = ALL_PAIRS
