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
