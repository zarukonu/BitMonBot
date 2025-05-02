# arbitrage/finder.py
import logging
from typing import Dict, List, Optional
import asyncio

from exchange_api.base_exchange import BaseExchange
from exchange_api.factory import ExchangeFactory
from arbitrage.opportunity import ArbitrageOpportunity
import config

logger = logging.getLogger('arbitrage')

class ArbitrageFinder:
    """
    Клас для пошуку арбітражних можливостей між біржами
    """
    def __init__(self, 
                 exchange_names: List[str], 
                 min_profit: float = config.MIN_PROFIT_THRESHOLD, 
                 include_fees: bool = config.INCLUDE_FEES,
                 fee_type: str = config.FEE_TYPE):
        self.exchange_names = exchange_names
        self.min_profit = min_profit
        self.include_fees = include_fees
        self.fee_type = fee_type.lower()  # 'maker' або 'taker'
        self.exchanges: Dict[str, BaseExchange] = {}
        
    async def initialize(self):
        """
        Ініціалізація об'єктів бірж
        """
        for name in self.exchange_names:
            try:
                self.exchanges[name] = ExchangeFactory.create(name)
                logger.info(f"Ініціалізовано біржу {name}")
            except Exception as e:
                logger.error(f"Помилка при ініціалізації біржі {name}: {e}")
    
    async def close_exchanges(self):
        """
        Закриття з'єднань з біржами
        """
        for name, exchange in self.exchanges.items():
            try:
                await exchange.close()
                logger.info(f"Закрито з'єднання з біржею {name}")
            except Exception as e:
                logger.error(f"Помилка при закритті з'єднання з біржею {name}: {e}")
    
    async def get_all_tickers(self, symbols: List[str]) -> Dict[str, Dict[str, Dict]]:
        """
        Отримання тікерів для всіх бірж
        """
        tasks = []
        for name, exchange in self.exchanges.items():
            tasks.append(self._get_exchange_tickers(name, exchange, symbols))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_tickers = {}
        for i, name in enumerate(self.exchanges.keys()):
            if isinstance(results[i], Exception):
                logger.error(f"Помилка при отриманні тікерів для {name}: {results[i]}")
                all_tickers[name] = {}
            else:
                all_tickers[name] = results[i]
        
        return all_tickers
    
    async def _get_exchange_tickers(self, exchange_name: str, exchange: BaseExchange, symbols: List[str]) -> Dict[str, Dict]:
        """
        Отримання тікерів для однієї біржі
        """
        try:
            tickers = await exchange.get_tickers(symbols)
            logger.info(f"Отримано {len(tickers)} тікерів для {exchange_name}")
            return tickers
        except Exception as e:
            logger.error(f"Помилка при отриманні тікерів для {exchange_name}: {e}")
            return {}
    
    async def find_opportunities(self, symbols: List[str] = None) -> List[ArbitrageOpportunity]:
        """
        Пошук арбітражних можливостей
        """
        if symbols is None:
            symbols = config.PAIRS
            
        opportunities = []
        
        # Отримуємо тікери для всіх бірж
        all_tickers = await self.get_all_tickers(symbols)
        
        # Для кожної валютної пари перевіряємо можливості арбітражу між біржами
        for symbol in symbols:
            # Збираємо ціни з усіх бірж для поточної пари
            symbol_prices = {}
            for exchange_name, tickers in all_tickers.items():
                if symbol in tickers:
                    # Якщо є і bid (ціна купівлі), і ask (ціна продажу)
                    if 'bid' in tickers[symbol] and 'ask' in tickers[symbol]:
                        symbol_prices[exchange_name] = {
                            'bid': tickers[symbol]['bid'],  # Максимальна ціна, за якою готові купити
                            'ask': tickers[symbol]['ask']   # Мінімальна ціна, за якою готові продати
                        }
            
            # Якщо маємо ціни з принаймні двох бірж
            if len(symbol_prices) >= 2:
                # Перевіряємо всі можливі комбінації бірж
                exchange_names = list(symbol_prices.keys())
                for i in range(len(exchange_names)):
                    for j in range(len(exchange_names)):
                        if i != j:  # Уникаємо порівняння біржі з самою собою
                            buy_exchange = exchange_names[i]
                            sell_exchange = exchange_names[j]
                            
                            # Ціна, за якою можемо купити на першій біржі
                            buy_price = symbol_prices[buy_exchange]['ask']
                            
                            # Ціна, за якою можемо продати на другій біржі
                            sell_price = symbol_prices[sell_exchange]['bid']
                            
                            # Обчислюємо потенційний прибуток
                            if buy_price > 0:  # Уникаємо ділення на нуль
                                # Розрахунок "сирого" прибутку без комісій
                                profit_percent = (sell_price - buy_price) / buy_price * 100
                                
                                # Отримуємо комісії для бірж
                                buy_fee = 0.0
                                sell_fee = 0.0
                                
                                if self.include_fees:
                                    # Отримуємо комісії відповідно до типу (maker або taker)
                                    if buy_exchange.lower() in config.EXCHANGE_FEES:
                                        buy_fee = config.EXCHANGE_FEES[buy_exchange.lower()].get(self.fee_type, 0.0)
                                    
                                    if sell_exchange.lower() in config.EXCHANGE_FEES:
                                        sell_fee = config.EXCHANGE_FEES[sell_exchange.lower()].get(self.fee_type, 0.0)
                                
                                # Розраховуємо чистий прибуток з урахуванням комісій
                                if self.include_fees and (buy_fee > 0 or sell_fee > 0):
                                    buy_with_fee = buy_price * (1 + buy_fee / 100)
                                    sell_with_fee = sell_price * (1 - sell_fee / 100)
                                    net_profit_percent = (sell_with_
