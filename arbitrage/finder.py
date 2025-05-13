# arbitrage/finder.py
import logging
from typing import Dict, List, Tuple, Optional
import asyncio
from datetime import datetime
import json
import os

from exchange_api.base_exchange import BaseExchange
from exchange_api.factory import ExchangeFactory
from arbitrage.opportunity import ArbitrageOpportunity
import config

logger = logging.getLogger('arbitrage')
all_opps_logger = logging.getLogger('all_opportunities')

class ArbitrageFinder:
    """
    Клас для пошуку арбітражних можливостей між біржами
    """
    def __init__(self, 
                 exchange_names: List[str], 
                 min_profit: float = config.MIN_PROFIT_THRESHOLD, 
                 include_fees: bool = config.INCLUDE_FEES,
                 buy_fee_type: str = config.BUY_FEE_TYPE,
                 sell_fee_type: str = config.SELL_FEE_TYPE):
        self.exchange_names = exchange_names
        self.min_profit = min_profit
        self.include_fees = include_fees
        self.buy_fee_type = buy_fee_type.lower()  # 'maker' або 'taker'
        self.sell_fee_type = sell_fee_type.lower()  # 'maker' або 'taker'
        self.exchanges: Dict[str, BaseExchange] = {}
        logger.info(f"Ініціалізовано ArbitrageFinder з min_profit={min_profit}%, include_fees={include_fees}")
        
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
    
    async def get_all_tickers(self, symbols: List[str] = None) -> Dict[str, Dict[str, Dict]]:
        """
        Отримання тікерів для всіх бірж з урахуванням підтримуваних пар
        """
        tasks = []
        
        for name, exchange in self.exchanges.items():
            # Визначаємо пари для конкретної біржі
            exchange_name = name.lower()
            exchange_symbols = []
            
            # Якщо symbols не вказано, використовуємо всі доступні для біржі
            if symbols is None:
                if exchange_name in config.EXCHANGE_SPECIFIC_PAIRS:
                    exchange_symbols = config.EXCHANGE_SPECIFIC_PAIRS[exchange_name]
                else:
                    exchange_symbols = config.ALL_PAIRS
            else:
                # Використовуємо тільки ті пари, які підтримуються біржею
                if exchange_name in config.EXCHANGE_SPECIFIC_PAIRS:
                    exchange_symbols = [s for s in symbols if s in config.EXCHANGE_SPECIFIC_PAIRS[exchange_name]]
                else:
                    exchange_symbols = symbols
                    
            if exchange_symbols:
                tasks.append(self._get_exchange_tickers(name, exchange, exchange_symbols))
                logger.debug(f"Додано задачу отримання тікерів для {name} ({len(exchange_symbols)} пар)")
            else:
                logger.warning(f"Не знайдено підтримуваних пар для біржі {name}")
                tasks.append(asyncio.sleep(0))  # Пуста задача
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_tickers = {}
        for i, name in enumerate(self.exchanges.keys()):
            if isinstance(results[i], Exception):
                logger.error(f"Помилка при отриманні тікерів для {name}: {results[i]}")
                all_tickers[name] = {}
            elif isinstance(results[i], dict):  # Перевіряємо, що результат - словник
                all_tickers[name] = results[i]
                logger.debug(f"Отримано {len(results[i])} тікерів для {name}")
            else:
                all_tickers[name] = {}
                logger.warning(f"Неочікуваний результат при отриманні тікерів для {name}: {type(results[i])}")
        
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
        all_possible_opportunities = []  # Для збереження всіх можливостей
        
        # Логуємо, які пари перевіряються
        logger.info(f"Починаємо пошук арбітражних можливостей для {len(symbols)} пар: {', '.join(symbols)}")
        
        # Отримуємо тікери для всіх бірж
        all_tickers = await self.get_all_tickers(symbols)
        
        # Перевіряємо, які пари доступні на яких біржах
        exchange_coverage = {}
        for exchange_name, tickers in all_tickers.items():
            exchange_pairs = [symbol for symbol in symbols if symbol in tickers]
            exchange_coverage[exchange_name] = exchange_pairs
            
            logger.info(f"Біржа {exchange_name}: Знайдено тікери для {len(exchange_pairs)} з {len(symbols)} пар")
            missing_pairs = set(symbols) - set(exchange_pairs)
            if missing_pairs:
                logger.info(f"Біржа {exchange_name}: Відсутні тікери для пар: {', '.join(missing_pairs)}")
        
        # Знаходимо пари, для яких є тікери на хоча б одній біржі
        all_pairs_with_prices = set()
        for exchange_name, tickers in all_tickers.items():
            for symbol in tickers:
                if symbol in symbols:
                    all_pairs_with_prices.add(symbol)
        
        logger.info(f"Знайдено тікери на хоча б одній біржі для {len(all_pairs_with_prices)} з {len(symbols)} пар")
        missing_pairs = set(symbols) - all_pairs_with_prices
        if missing_pairs:
            logger.info(f"Не знайдено тікерів для пар: {', '.join(missing_pairs)}")
            
        # Для кожної валютної пари перевіряємо можливості арбітражу між біржами
        for symbol in symbols:
            # Збираємо ціни з усіх бірж для поточної пари
            symbol_prices = {}
            for exchange_name, tickers in all_tickers.items():
                if symbol in tickers and tickers[symbol]:
                    # Якщо є і bid (ціна купівлі), і ask (ціна продажу)
                    if 'bid' in tickers[symbol] and 'ask' in tickers[symbol]:
                        # Додаткова перевірка на None
                        bid = tickers[symbol]['bid']
                        ask = tickers[symbol]['ask']
                        if bid is not None and ask is not None:
                            symbol_prices[exchange_name] = {
                                'bid': bid,  # Максимальна ціна, за якою готові купити
                                'ask': ask   # Мінімальна ціна, за якою готові продати
                            }
            
            # Якщо маємо ціни з принаймні двох бірж
            if len(symbol_prices) >= 2:
                logger.debug(f"Знайдено ціни для {symbol} на {len(symbol_prices)} біржах: {', '.join(symbol_prices.keys())}")
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
                            
                            # Перевіряємо, що ціни не None
                            if buy_price is not None and sell_price is not None and buy_price > 0:
                                # Обчислюємо потенційний прибуток
                                profit_percent = (sell_price - buy_price) / buy_price * 100
                                
                                # Отримуємо відповідні комісії для бірж (окремо для купівлі та продажу)
                                buy_fee = 0.0
                                sell_fee = 0.0
                                
                                if self.include_fees:
                                    # Комісія для купівлі з використанням відповідного типу (maker/taker)
                                    if buy_exchange.lower() in config.EXCHANGE_FEES:
                                        buy_fee = config.EXCHANGE_FEES[buy_exchange.lower()].get(self.buy_fee_type, 0.0)
                                    
                                    # Комісія для продажу з використанням відповідного типу (maker/taker)
                                    if sell_exchange.lower() in config.EXCHANGE_FEES:
                                        sell_fee = config.EXCHANGE_FEES[sell_exchange.lower()].get(self.sell_fee_type, 0.0)
                                
                                # Розраховуємо чистий прибуток з урахуванням комісій
                                if self.include_fees and (buy_fee > 0 or sell_fee > 0):
                                    buy_with_fee = buy_price * (1 + buy_fee / 100)
                                    sell_with_fee = sell_price * (1 - sell_fee / 100)
                                    net_profit_percent = (sell_with_fee - buy_with_fee) / buy_with_fee * 100
                                    
                                    # Використовуємо чистий прибуток для порівняння з порогом
                                    compare_profit = net_profit_percent
                                else:
                                    # Якщо комісії вимкнені, використовуємо "сирий" прибуток
                                    compare_profit = profit_percent
                                    net_profit_percent = None
                                
                                # Форматуємо рядок з чистим прибутком
                                if net_profit_percent is not None:
                                    net_profit_str = f"{net_profit_percent:.4f}"
                                else:
                                    net_profit_str = "0.0000"
                                
                                # Логуємо для діагностики - всі комбінації, навіть ті, що не дають прибуток
                                logger.debug(
                                    f"{symbol}: {buy_exchange} -> {sell_exchange}: "
                                    f"buy={buy_price:.8f}, sell={sell_price:.8f}, "
                                    f"profit={profit_percent:.4f}%, "
                                    f"net_profit={net_profit_str}%"
                                )
                                
                                # Логуємо всі можливості з позитивним прибутком, навіть якщо не проходять за порогом
                                if profit_percent > 0:
                                    # Додаємо в список всіх можливостей
                                    opportunity_data = {
                                        "symbol": symbol,
                                        "buy_exchange": buy_exchange,
                                        "sell_exchange": sell_exchange,
                                        "buy_price": buy_price,
                                        "sell_price": sell_price,
                                        "profit_percent": profit_percent,
                                        "buy_fee": buy_fee,
                                        "sell_fee": sell_fee,
                                        "net_profit_percent": net_profit_percent if net_profit_percent is not None else 0.0,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    all_possible_opportunities.append(opportunity_data)
                                
                                # Якщо прибуток перевищує мінімальний поріг
                                if compare_profit >= self.min_profit:
                                    opportunity = ArbitrageOpportunity(
                                        symbol=symbol,
                                        buy_exchange=buy_exchange,
                                        sell_exchange=sell_exchange,
                                        buy_price=buy_price,
                                        sell_price=sell_price,
                                        profit_percent=profit_percent,
                                        buy_fee=buy_fee if self.include_fees else 0.0,
                                        sell_fee=sell_fee if self.include_fees else 0.0,
                                        net_profit_percent=net_profit_percent,
                                        buy_fee_type=self.buy_fee_type if self.include_fees else "",
                                        sell_fee_type=self.sell_fee_type if self.include_fees else ""
                                    )
                                    opportunities.append(opportunity)
                                    
                                    # ВИДІЛЕНО ВЕЛИКИМИ ЛІТЕРАМИ для легшого знаходження в логах
                                    logger.info(
                                        f"ЗНАЙДЕНО АРБІТРАЖНУ МОЖЛИВІСТЬ: {symbol} "
                                        f"купити на {buy_exchange} за {buy_price:.8f} (комісія {buy_fee}%), "
                                        f"продати на {sell_exchange} за {sell_price:.8f} (комісія {sell_fee}%). "
                                        f"Прибуток: {profit_percent:.2f}%, "
                                        f"Чистий прибуток: {net_profit_str}%"
                                    )
                                elif profit_percent >= self.min_profit and (net_profit_percent is None or net_profit_percent < self.min_profit):
                                    # Логуємо випадки, коли є потенційний прибуток, але комісії його "з'їдають"
                                    logger.info(
                                        f"ВІДХИЛЕНО ЧЕРЕЗ КОМІСІЇ: {symbol} "
                                        f"купити на {buy_exchange} за {buy_price:.8f} (комісія {buy_fee}%), "
                                        f"продати на {sell_exchange} за {sell_price:.8f} (комісія {sell_fee}%). "
                                        f"Прибуток: {profit_percent:.2f}%, "
                                        f"Чистий прибуток: {net_profit_str}% < {self.min_profit}%"
                                    )
            else:
                logger.debug(f"Недостатньо бірж для арбітражу для {symbol} (знайдено цін: {len(symbol_prices)})")
        
        # Логуємо всі можливості, навіть якщо вони не пройшли за порогом
        if all_possible_opportunities:
            # Сортуємо за чистим прибутком
            all_possible_opportunities.sort(key=lambda x: x['net_profit_percent'], reverse=True)
            
            # Логуємо у спеціальний файл
            opportunity_log = f"===== ЗВІТ ПРО ВСІ МОЖЛИВОСТІ ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) =====\n"
            opportunity_log += f"Всього знайдено {len(all_possible_opportunities)} потенційних можливостей:\n"
            
            for i, opp in enumerate(all_possible_opportunities, 1):
                opportunity_log += (
                    f"{i}. {opp['symbol']}: {opp['buy_exchange']} → {opp['sell_exchange']}, "
                    f"Прибуток {opp['profit_percent']:.4f}%, "
                    f"Чистий прибуток {opp['net_profit_percent']:.4f}%, "
                    f"Buy: {opp['buy_price']}, Sell: {opp['sell_price']}\n"
                )
            
            all_opps_logger.info(opportunity_log)
            
            # Також зберігаємо всі можливості в JSON файл для аналізу
            opportunities_data = {
                "timestamp": datetime.now().isoformat(),
                "total": len(all_possible_opportunities),
                "opportunities": all_possible_opportunities,
                "min_profit_threshold": self.min_profit
            }
            
            try:
                # Створюємо директорію, якщо вона не існує
                os.makedirs("data", exist_ok=True)
                
                # Зберігаємо з ім'ям файлу на основі поточної дати та часу
                filename = f"data/opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, "w") as f:
                    json.dump(opportunities_data, f, indent=2)
                    
                logger.info(f"Збережено {len(all_possible_opportunities)} потенційних можливостей у файл {filename}")
            except Exception as e:
                logger.error(f"Помилка при збереженні можливостей у JSON: {e}")
        
        logger.info(f"Всього знайдено {len(opportunities)} арбітражних можливостей")
        return opportunities
