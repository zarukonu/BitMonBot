# exchange_api/kraken_api.py
import ccxt.async_support as ccxt
from typing import Dict, List, Tuple, Optional
import logging

from exchange_api.base_exchange import BaseExchange
import config

logger = logging.getLogger('main')

class KrakenAPI(BaseExchange):
    """
    Клас для роботи з API Kraken
    """
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret,
            'timeout': config.REQUEST_TIMEOUT * 1000,  # в мілісекундах
            'enableRateLimit': config.RATE_LIMIT_RETRY
        })
        
    async def get_ticker(self, symbol: str) -> Dict:
        """
        Отримати поточні ціни для валютної пари
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            logger.error(f"Помилка при отриманні тікера для {symbol} на Kraken: {e}")
            return {}
    
    async def get_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Отримати поточні ціни для списку валютних пар
        """
        try:
            tickers = await self.exchange.fetch_tickers(symbols)
            return tickers
        except Exception as e:
            logger.error(f"Помилка при отриманні тікерів на Kraken: {e}")
            # Спробуємо отримати кожен тікер окремо
            result = {}
            for symbol in symbols:
                try:
                    ticker = await self.get_ticker(symbol)
                    if ticker:
                        result[symbol] = ticker
                except Exception as e:
                    logger.error(f"Помилка при отриманні тікера для {symbol} на Kraken: {e}")
            return result
    
    async def get_orderbook(self, symbol: str, limit: int = 10) -> Dict:
        """
        Отримати книгу ордерів для валютної пари
        """
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit)
            return orderbook
        except Exception as e:
            logger.error(f"Помилка при отриманні книги ордерів для {symbol} на Kraken: {e}")
            return {}
            
    async def check_order_book_depth(self, symbol: str, amount: float) -> Tuple[bool, Optional[float]]:
        """
        Перевіряє, чи достатньо глибини ордербуку для виконання угоди заданого розміру
        
        Args:
            symbol (str): Символ валютної пари
            amount (float): Розмір угоди
            
        Returns:
            Tuple[bool, Optional[float]]:
                - bool: True, якщо глибина достатня, False інакше
                - Optional[float]: Середня ціна виконання або None, якщо глибина недостатня
        """
        try:
            # Отримуємо книгу ордерів з більшою глибиною
            orderbook = await self.get_orderbook(symbol, limit=100)
            
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                return False, None
            
            # Для покупки використовуємо asks, для продажу - bids
            asks = orderbook['asks']  # Ордери на продаж
            
            total_volume = 0.0
            total_cost = 0.0
            
            # Перевіряємо, чи достатньо обсягу для покупки
            for price, volume in asks:
                available_volume = min(volume, amount - total_volume)
                total_volume += available_volume
                total_cost += available_volume * price
                
                if total_volume >= amount:
                    avg_price = total_cost / total_volume
                    return True, avg_price
                    
            return False, None
            
        except Exception as e:
            logger.error(f"Помилка при перевірці глибини ордербуку для {symbol} на Kraken: {e}")
            return False, None
    
    async def close(self):
        """
        Закрити з'єднання з біржею
        """
        await self.exchange.close()
