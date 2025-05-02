# arbitrage/fee_calculator.py
import logging
from typing import Dict, List, Optional, Tuple

import config

logger = logging.getLogger('arbitrage')

class FeeCalculator:
    """
    Клас для розрахунку комісій при виконанні арбітражних операцій
    """
    def __init__(self):
        self.fees_config = config.EXCHANGE_FEES
        
    def calculate_cross_exchange_fees(self, buy_exchange: str, sell_exchange: str, 
                                      symbol: str, amount: float) -> float:
        """
        Розрахунок комісій для крос-біржового арбітражу
        
        Args:
            buy_exchange (str): Назва біржі для купівлі
            sell_exchange (str): Назва біржі для продажу
            symbol (str): Торгова пара (наприклад, 'BTC/USDT')
            amount (float): Сума угоди в базовій валюті
            
        Returns:
            float: Загальна комісія у відсотках
        """
        buy_exchange = buy_exchange.lower()
        sell_exchange = sell_exchange.lower()
        
        # Отримуємо базову та квотовану валюти
        base_currency, quote_currency = symbol.split('/')
        
        # Комісія за купівлю (taker fee)
        buy_fee_percent = self._get_trading_fee(buy_exchange, 'taker')
        
        # Комісія за продаж (taker fee)
        sell_fee_percent = self._get_trading_fee(sell_exchange, 'taker')
        
        # Комісія за виведення базової валюти з біржі покупки
        withdrawal_fee = self._get_withdrawal_fee(buy_exchange, base_currency, amount)
        withdrawal_fee_percent = (withdrawal_fee / amount) * 100
        
        # Загальна комісія у відсотках
        total_fee_percent = buy_fee_percent + sell_fee_percent + withdrawal_fee_percent
        
        logger.debug(f"Комісії для {buy_exchange}->{sell_exchange} ({symbol}): "
                    f"Купівля: {buy_fee_percent}%, Продаж: {sell_fee_percent}%, "
                    f"Виведення: {withdrawal_fee_percent}%, Загалом: {total_fee_percent}%")
        
        return total_fee_percent
    
    def calculate_triangular_fees(self, exchange: str, path: List[str], 
                                 amount: float) -> float:
        """
        Розрахунок комісій для трикутного арбітражу
        
        Args:
            exchange (str): Назва біржі
            path (List[str]): Шлях для трикутного арбітражу, наприклад ['USDT', 'BTC', 'ETH', 'USDT']
            amount (float): Початкова сума в першій валюті
            
        Returns:
            float: Загальна комісія у відсотках
        """
        exchange = exchange.lower()
        
        # Кількість угод у трикутному арбітражі
        trade_count = len(path) - 1
        
        # Отримуємо комісію за угоду (taker fee)
        taker_fee = self._get_trading_fee(exchange, 'taker')
        
        # Загальна комісія у відсотках
        total_fee_percent = taker_fee * trade_count
        
        logger.debug(f"Комісії для трикутного арбітражу на {exchange} ({' -> '.join(path)}): "
                    f"За угоду: {taker_fee}%, Всього угод: {trade_count}, "
                    f"Загальна комісія: {total_fee_percent}%")
        
        return total_fee_percent
    
    def _get_trading_fee(self, exchange: str, fee_type: str) -> float:
        """
        Отримати комісію за угоду з урахуванням можливих знижок
        
        Args:
            exchange (str): Назва біржі
            fee_type (str): Тип комісії ('maker' або 'taker')
            
        Returns:
            float: Комісія у відсотках
        """
        exchange = exchange.lower()
        
        if exchange not in self.fees_config:
            logger.warning(f"Не знайдено налаштування комісій для біржі {exchange}. "
                          f"Використовуємо комісію за замовчуванням: 0.2%")
            return 0.2
        
        # Базова комісія
        base_fee = self.fees_config[exchange].get(fee_type, 0.2)
        
        # Перевірка на наявність токена знижки
        discount_token = self.fees_config[exchange].get('discount_token')
        discount_percent = self.fees_config[exchange].get('discount_percent', 0)
        
        # Поки що припускаємо, що ми завжди маємо токен знижки, якщо він є
        # В реальному випадку тут була б перевірка наявності токену у користувача
        if discount_token and discount_percent > 0:
            discounted_fee = base_fee * (1 - discount_percent / 100)
            logger.debug(f"Застосовано знижку {discount_percent}% для {exchange} з токеном {discount_token}. "
                        f"Комісія {fee_type}: {base_fee}% -> {discounted_fee}%")
            return discounted_fee
        
        return base_fee
    
    def _get_withdrawal_fee(self, exchange: str, currency: str, amount: float) -> float:
        """
        Отримати комісію за виведення валюти
        
        Args:
            exchange (str): Назва біржі
            currency (str): Валюта
            amount (float): Сума виведення
            
        Returns:
            float: Комісія за виведення в одиницях валюти
        """
        exchange = exchange.lower()
        
        if exchange not in self.fees_config:
            logger.warning(f"Не знайдено налаштування комісій для біржі {exchange}. "
                          f"Використовуємо комісію за замовчуванням: 0.1")
            return 0.1
        
        # Отримуємо комісію за виведення для даної валюти або за замовчуванням
        withdrawal_fees = self.fees_config[exchange].get('withdrawal', {})
        fee = withdrawal_fees.get(currency, withdrawal_fees.get('DEFAULT', 0.1))
        
        return fee
