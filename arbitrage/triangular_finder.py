# arbitrage/triangular_finder.py
import logging
from typing import Dict, List, Optional, Tuple
import asyncio
import time

from exchange_api.base_exchange import BaseExchange
from arbitrage.opportunity import ArbitrageOpportunity
from arbitrage.fee_calculator import FeeCalculator
import config

logger = logging.getLogger('triangular')  # Змінюємо логер на 'triangular'

class TriangularArbitrageFinder:
    """
    Клас для пошуку трикутних арбітражних можливостей на одній біржі
    """
    def __init__(self, exchange: BaseExchange, 
                 base_currency: str = "USDT", 
                 min_profit: float = config.TRIANGULAR_MIN_PROFIT_THRESHOLD):  # Використовуємо новий параметр
        self.exchange = exchange
        self.exchange_name = exchange.name
        self.base_currency = base_currency
        self.min_profit = min_profit
        self.fee_calculator = FeeCalculator()
        self.paths = config.TRIANGULAR_PATHS
        self.market_cache = {}  # Кеш для збереження підтримуваних форматів пар

    async def initialize_market_cache(self):
        """
        Ініціалізує кеш підтримуваних ринків для біржі
        """
        try:
            # Отримуємо всі доступні ринки на біржі
            markets = await self.exchange.exchange.fetch_markets()
            
            # Заповнюємо кеш
            for market in markets:
                symbol = market['symbol']
                self.market_cache[symbol] = True
                
            logger.info(f"Ініціалізовано кеш ринків для {self.exchange_name}: {len(self.market_cache)} ринків")
        except Exception as e:
            logger.error(f"Помилка при ініціалізації кешу ринків для {self.exchange_name}: {e}")
    
    async def find_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Пошук трикутних арбітражних можливостей
        
        Returns:
            List[ArbitrageOpportunity]: Список знайдених можливостей
        """
        opportunities = []
        
        # Ініціалізуємо кеш ринків, якщо ще не зроблено
        if not self.market_cache:
            await self.initialize_market_cache()
        
        # Для кожного шляху в конфігурації
        for path in self.paths:
            try:
                # Перевіряємо чи шлях починається і закінчується тією ж валютою
                if path[0] != path[-1]:
                    logger.warning(f"Шлях {path} не є циклічним. Пропускаємо.")
                    continue
                
                # Перевіряємо можливість для шляху
                opportunity = await self._check_path(path)
                if opportunity:
                    opportunities.append(opportunity)
                    
            except Exception as e:
                logger.error(f"Помилка при перевірці шляху {path}: {e}")
        
        return opportunities
                
    async def _check_path(self, path: List[str]) -> Optional[ArbitrageOpportunity]:
        """
        Перевіряє конкретний трикутний шлях на наявність арбітражних можливостей
        
        Args:
            path (List[str]): Список валют для арбітражного шляху, наприклад ['USDT', 'BTC', 'ETH', 'USDT']
            
        Returns:
            Optional[ArbitrageOpportunity]: Арбітражна можливість, якщо вона є, або None
        """
        try:
            # Створюємо пари для кожного переходу в шляху
            pairs = []
            for i in range(len(path) - 1):
                from_currency = path[i]
                to_currency = path[i + 1]
                
                # Спробуємо знайти правильний формат пари
                pair_info = await self._find_valid_pair_format(from_currency, to_currency)
                
                if pair_info is None:
                    # Якщо формат пари не знайдено, пропускаємо цей шлях
                    logger.warning(f"Не вдалося отримати тікер для пари {from_currency}/{to_currency} або {to_currency}/{from_currency}. Пропускаємо шлях {path}.")
                    return None
                
                pairs.append(pair_info)
            
            # Отримуємо тікери для всіх пар
            tickers = {}
            for pair_format, _ in pairs:
                ticker = await self.exchange.get_ticker(pair_format)
                if not ticker:
                    logger.warning(f"Не вдалося отримати тікер для пари {pair_format}. Пропускаємо шлях {path}.")
                    return None
                tickers[pair_format] = ticker
            
            # Розраховуємо прибуток для шляху
            initial_amount = 100  # Припускаємо, що починаємо зі 100 одиниць першої валюти
            current_amount = initial_amount
            rates = []
            
            # Проходимо по кожній парі в шляху
            for (pair_format, direction) in pairs:
                ticker = tickers[pair_format]
                
                if 'bid' not in ticker or 'ask' not in ticker:
                    logger.warning(f"Тікер для пари {pair_format} не містить необхідних даних. Пропускаємо шлях {path}.")
                    return None
                
                if direction == "buy":
                    # Купуємо базову валюту за котирувальну
                    rate = ticker['ask']  # Ціна, за якою можемо купити
                    current_amount = current_amount / rate
                else:
                    # Продаємо базову валюту за котирувальну
                    rate = ticker['bid']  # Ціна, за якою можемо продати
                    current_amount = current_amount * rate
                
                rates.append(rate)
            
            # Розраховуємо прибуток
            profit_percent = ((current_amount / initial_amount) - 1) * 100
            
            # Логуємо для діагностики всі перевірені шляхи
            logger.debug(f"Перевірено шлях {' -> '.join(path)} на {self.exchange_name}: прибуток {profit_percent:.4f}%")
            
            # Якщо прибуток перевищує мінімальний поріг
            if profit_percent >= self.min_profit:
                # Розраховуємо комісії
                fees_percent = self.fee_calculator.calculate_triangular_fees(
                    self.exchange_name, path, initial_amount
                )
                
                # Розраховуємо чистий прибуток
                net_profit_percent = profit_percent - fees_percent
                
                # Перевіряємо, чи чистий прибуток все ще вище порогу
                if net_profit_percent >= config.MIN_NET_PROFIT_THRESHOLD:
                    # Створюємо об'єкт арбітражної можливості
                    opportunity = ArbitrageOpportunity(
                        symbol=f"{path[0]}->{path[1]}->{path[2]}",
                        buy_exchange=self.exchange_name,
                        sell_exchange=self.exchange_name,
                        buy_price=rates[0],
                        sell_price=rates[-1],
                        profit_percent=profit_percent,
                        opportunity_type="triangular",
                        estimated_fees=fees_percent,
                        net_profit_percent=net_profit_percent,
                        path=path
                    )
                    
                    logger.info(f"Знайдено трикутну арбітражну можливість на {self.exchange_name}: "
                              f"Шлях: {' -> '.join(path)}, Прибуток: {net_profit_percent:.2f}% після комісій")
                    
                    return opportunity
                else:
                    # Логуємо випадки, коли прибуток є, але комісії його з'їдають
                    logger.debug(f"Знайдено невигідну можливість на {self.exchange_name}: "
                               f"Шлях: {' -> '.join(path)}, Прибуток: {profit_percent:.2f}%, "
                               f"Чистий прибуток: {net_profit_percent:.2f}% (нижче порогу {config.MIN_NET_PROFIT_THRESHOLD}%)")
            
            return None
            
        except Exception as e:
            logger.error(f"Помилка при перевірці шляху {path}: {e}")
            return None
            
    async def _find_valid_pair_format(self, currency1: str, currency2: str) -> Optional[Tuple[str, str]]:
        """
        Шукає валідний формат пари для двох валют
        
        Args:
            currency1 (str): Перша валюта
            currency2 (str): Друга валюта
            
        Returns:
            Optional[Tuple[str, str]]: (формат_пари, напрямок) або None, якщо формат не знайдено
                формат_пари: рядок у форматі 'XXX/YYY'
                напрямок: 'buy' або 'sell'
        """
        # Спробуємо два можливих формати пари
        format1 = f"{currency1}/{currency2}"
        format2 = f"{currency2}/{currency1}"
        
        # Якщо кеш ініціалізовано, перевіряємо чи є такі формати в кеші
        if self.market_cache:
            if format1 in self.market_cache:
                return (format1, 'sell')  # Ми продаємо currency1 за currency2
            elif format2 in self.market_cache:
                return (format2, 'buy')   # Ми купуємо currency2 за currency1
        
        # Якщо кеш не допоміг, спробуємо безпосередньо отримати тікер
        try:
            ticker = await self.exchange.get_ticker(format1)
            if ticker:
                return (format1, 'sell')
        except Exception:
            # Не вдалося отримати тікер для першого формату, спробуємо другий
            pass
            
        try:
            ticker = await self.exchange.get_ticker(format2)
            if ticker:
                return (format2, 'buy')
        except Exception:
            # Не вдалося отримати тікер для другого формату
            pass
            
        # Якщо жоден формат не працює, повертаємо None
        return None
