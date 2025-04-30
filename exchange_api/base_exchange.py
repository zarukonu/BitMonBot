# exchange_api/base_exchange.py
from abc import ABC, abstractmethod
from typing import Dict, List

class BaseExchange(ABC):
    """
    Абстрактний базовий клас для інтеграції з біржами
    """
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        self.api_key = api_key
        self.api_secret = api_secret
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict:
        """
        Отримати поточні ціни для валютної пари
        
        Args:
            symbol (str): Символ валютної пари (наприклад, "BTC/USDT")
            
        Returns:
            Dict: Словник з даними тікера
        """
        pass
    
    @abstractmethod
    async def get_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Отримати поточні ціни для списку валютних пар
        
        Args:
            symbols (List[str]): Список символів валютних пар
            
        Returns:
            Dict[str, Dict]: Словник тікерів для кожної пари
        """
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 10) -> Dict:
        """
        Отримати книгу ордерів для валютної пари
        
        Args:
            symbol (str): Символ валютної пари
            limit (int): Кількість ордерів для отримання
            
        Returns:
            Dict: Словник з книгою ордерів
        """
        pass
    
    @abstractmethod
    async def close(self):
        """
        Закрити з'єднання з біржею
        """
        pass
