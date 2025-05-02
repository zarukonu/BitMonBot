# exchange_api/binance_api.py
import ccxt.async_support as ccxt
from typing import Dict, List
import asyncio
import logging

from exchange_api.base_exchange import BaseExchange
import config

logger = logging.getLogger('main')

class BinanceAPI(BaseExchange):
    """
    Клас для роботи з API Binance
    """
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.exchange = ccxt.binance({
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
            logger.error(f"Помилка при отриманні тікера для {symbol} на Binance: {e}")
            return {}
    
    async def get_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Отримати поточні ціни для списку валютних пар
        """
        try:
            # Метод fetch_tickers підтримує отримання даних для кількох символів одразу
            tickers = await self.exchange.fetch_tickers(symbols)
            return tickers
        except Exception as e:
            logger.error(f"Помилка при отриманні тікерів на Binance: {e}")
            # Спробуємо отримати кожен тікер окремо
            result = {}
            for symbol in symbols:
                try:
                    ticker = await self.get_ticker(symbol)
                    if ticker:
                        result[symbol] = ticker
                except Exception as e:
                    logger.error(f"Помилка при отриманні тікера для {symbol} на Binance: {e}")
            return result
    
    async def get_orderbook(self, symbol: str, limit: int = 10) -> Dict:
        """
        Отримати книгу ордерів для валютної пари
        """
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit)
            return orderbook
        except Exception as e:
            logger.error(f"Помилка при отриманні книги ордерів для {symbol} на Binance: {e}")
            return {}
    
    async def check_order_book_depth(self, symbol: str, amount: float) -> Dict:
        """
        Перевіряє глибину ордербуку для виконання угоди заданого розміру
        
        Args:
            symbol (str): Символ валютної пари
            amount (float): Обсяг для купівлі (від'ємне значення) або продажу (додатне)
            
        Returns:
            Dict: Результат аналізу з інформацією про ліквідність
        """
        try:
            # Отримуємо ордербук з більшою глибиною
            orderbook = await self.get_orderbook(symbol, 100)
            
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                logger.error(f"Не вдалося отримати дані ордербуку для {symbol} на Binance")
                return {
                    "success": False,
                    "error": "Не вдалося отримати дані ордербуку",
                    "max_amount": 0,
                    "expected_slippage": 0
                }
            
            # Для продажу використовуємо біди (bids)
            if amount > 0:
                return self._analyze_order_book_side(orderbook['bids'], amount, True)
            # Для купівлі використовуємо аски (asks)
            else:
                return self._analyze_order_book_side(orderbook['asks'], abs(amount), False)
                
        except Exception as e:
            logger.error(f"Помилка при перевірці глибини ордербуку для {symbol} на Binance: {e}")
            return {
                "success": False,
                "error": str(e),
                "max_amount": 0,
                "expected_slippage": 0
            }
            
    def _analyze_order_book_side(self, orders, amount: float, is_bid: bool) -> Dict:
        """
        Аналізує одну сторону ордербуку (біди або аски)
        
        Args:
            orders: Список ордерів
            amount (float): Обсяг для виконання
            is_bid (bool): True якщо аналізуємо біди, False якщо аски
            
        Returns:
            Dict: Результат аналізу
        """
        total_volume = 0
        weighted_price = 0
        
        for price_str, volume_str in orders:
            price = float(price_str)
            volume = float(volume_str)
            
            # Скільки криптовалюти можемо купити/продати за цією ціною
            available_volume = min(amount - total_volume, volume)
            
            if available_volume <= 0:
                break
                
            weighted_price += price * available_volume
            total_volume += available_volume
            
            if total_volume >= amount:
                break
        
        # Якщо недостатньо ліквідності
        if total_volume < amount:
            return {
                "success": False,
                "error": f"Недостатня глибина ордербуку. Доступно: {total_volume}, потрібно: {amount}",
                "max_amount": total_volume,
                "expected_slippage": 0
            }
        
        # Розраховуємо середньозважену ціну і прослизання
        average_price = weighted_price / total_volume
        best_price = float(orders[0][0])
        
        # Для бідів (продаж) та асків (купівля) прослизання розраховується по-різному
        if is_bid:
            slippage = (best_price - average_price) / best_price * 100
        else:
            slippage = (average_price - best_price) / best_price * 100
        
        return {
            "success": T
