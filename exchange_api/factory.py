# exchange_api/factory.py
from typing import Dict, Type
from exchange_api.base_exchange import BaseExchange
from exchange_api.binance_api import BinanceAPI
from exchange_api.kucoin_api import KuCoinAPI
from exchange_api.kraken_api import KrakenAPI
import config

class ExchangeFactory:
    """
    Фабрика для створення об'єктів бірж
    """
    _exchanges: Dict[str, Type[BaseExchange]] = {
        'binance': BinanceAPI,
        'kucoin': KuCoinAPI,
        'kraken': KrakenAPI
    }
    
    @classmethod
    def create(cls, exchange_name: str) -> BaseExchange:
        """
        Створює об'єкт біржі за її назвою
        
        Args:
            exchange_name (str): Назва біржі ('binance', 'kucoin', 'kraken')
            
        Returns:
            BaseExchange: Об'єкт біржі
            
        Raises:
            ValueError: Якщо біржа не підтримується
        """
        exchange_name = exchange_name.lower()
        
        if exchange_name not in cls._exchanges:
            raise ValueError(f"Біржа {exchange_name} не підтримується")
        
        if exchange_name == 'binance':
            return cls._exchanges[exchange_name](
                api_key=config.BINANCE_API_KEY,
                api_secret=config.BINANCE_API_SECRET
            )
        elif exchange_name == 'kucoin':
            return cls._exchanges[exchange_name](
                api_key=config.KUCOIN_API_KEY,
                api_secret=config.KUCOIN_API_SECRET,
                password=config.KUCOIN_API_PASSPHRASE
            )
        elif exchange_name == 'kraken':
            return cls._exchanges[exchange_name](
                api_key=config.KRAKEN_API_KEY,
                api_secret=config.KRAKEN_API_SECRET
            )
