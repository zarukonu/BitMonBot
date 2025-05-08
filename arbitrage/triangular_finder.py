# arbitrage/triangular_finder.py
import logging
from typing import Dict, List, Optional
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
        
    async def find_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Пошук трикутних арбітражних можливостей
        
        Returns:
            List[ArbitrageOpportunity]: Список знайдених можливостей
        """
        opportunities = []
        
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
                
                # Формуємо торгову пару в правильному форматі
                # Перевіряємо, яка валюта є базовою, а яка котирувальною
                if self._is_base_currency(from_currency, to_currency):
                    pair = f"{from_currency}/{to_currency}"
                    direction = "sell"  # Продаємо базову валюту
                else:
                    pair = f"{to_currency}/{from_currency}"
                    direction = "buy"   # Купуємо базову валюту
                
                pairs.append((pair, direction))
            
            # Отримуємо тікери для всіх пар
            tickers = {}
            for pair, _ in pairs:
                ticker = await self.exchange.get_ticker(pair)
                if not ticker:
                    logger.warning(f"Не вдалося отримати тікер для пари {pair}. Пропускаємо шлях {path}.")
                    return None
                tickers[pair] = ticker
            
            # Розраховуємо прибуток для шляху
            initial_amount = 100  # Припускаємо, що починаємо зі 100 одиниць першої валюти
            current_amount = initial_amount
            rates = []
            
            # Проходимо по кожній парі в шляху
            for (pair, direction) in pairs:
                ticker = tickers[pair]
                
                if 'bid' not in ticker or 'ask' not in ticker:
                    logger.warning(f"Тікер для пари {pair} не містить необхідних даних. Пропускаємо шлях {path}.")
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
            
            # Добавимо логування для всіх перевірених шляхів, навіть якщо вони не прибуткові
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
    
    def _is_base_currency(self, currency1: str, currency2: str) -> bool:
        """
        Визначає, яка з двох валют є базовою в торговій парі
        
        В реальному проекті це було б більш складно і залежало б від правил біржі.
        Для простоти припускаємо, що базовою є перша валюта в цьому порядку:
        BTC, ETH, BNB, USDT, інші.
        
        Args:
            currency1 (str): Перша валюта
            currency2 (str): Друга валюта
            
        Returns:
            bool: True, якщо currency1 є базовою валютою, False інакше
        """
        currency_priority = {"BTC": 1, "ETH": 2, "BNB": 3, "USDT": 4}
        
        priority1 = currency_priority.get(currency1, 5)
        priority2 = currency_priority.get(currency2, 5)
        
        return priority1 < priority2
