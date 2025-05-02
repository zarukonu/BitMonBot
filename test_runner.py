# test_runner.py
import asyncio
import logging
import sys
import random
from datetime import datetime

import config
import logger
from telegram_worker import TelegramWorker
from arbitrage.opportunity import ArbitrageOpportunity

# Отримуємо логер
test_logger = logging.getLogger('main')

async def test_telegram_notifications():
    """
    Тестує надсилання повідомлень у Telegram
    """
    telegram_worker = TelegramWorker(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    
    try:
        # Запускаємо Telegram Worker
        await telegram_worker.start()
        
        test_logger.info("Тест розпочато")
        
        # Додаємо тестові повідомлення в чергу
        await telegram_worker.send_message("🧪 Тестове повідомлення 1")
        await telegram_worker.send_message("🧪 Тестове повідомлення 2")
        
        # Додаємо форматоване повідомлення
        await telegram_worker.send_message(
            "<b>Форматоване повідомлення</b>\n"
            "<i>Курсивний текст</i>\n"
            "<code>Код</code>",
            parse_mode="HTML"
        )
        
        # Створюємо тестові арбітражні можливості
        pairs = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT", "BNB/USDT"]
        exchanges = ["Binance", "KuCoin", "Kraken"]
        
        # Додаємо повідомлення про тестування з комісіями
        await telegram_worker.send_message(
            "<b>🧪 Початок тестування арбітражних можливостей</b>\n"
            "Буде створено кілька тестових арбітражних можливостей з різними комісіями",
            parse_mode="HTML"
        )
        
        # Отримуємо комісії з конфігурації для реалістичних тестів
        fee_configs = {
            "Binance": {
                "buy": config.EXCHANGE_FEES["binance"][config.BUY_FEE_TYPE],
                "sell": config.EXCHANGE_FEES["binance"][config.SELL_FEE_TYPE]
            },
            "KuCoin": {
                "buy": config.EXCHANGE_FEES["kucoin"][config.BUY_FEE_TYPE],
                "sell": config.EXCHANGE_FEES["kucoin"][config.SELL_FEE_TYPE]
            },
            "Kraken": {
                "buy": config.EXCHANGE_FEES["kraken"][config.BUY_FEE_TYPE],
                "sell": config.EXCHANGE_FEES["kraken"][config.SELL_FEE_TYPE]
            }
        }
        
        # Генеруємо кілька арбітражних можливостей з різним рівнем прибутковості
        profit_scenarios = [
            {"profit": random.uniform(0.5, 0.9), "type": "низького"},
            {"profit": random.uniform(1.0, 1.9), "type": "середнього"},
            {"profit": random.uniform(2.0, 4.9), "type": "високого"},
            {"profit": random.uniform(5.0, 10.0), "type": "надвисокого"}
        ]
        
        for scenario in profit_scenarios:
            # Випадково вибираємо пару та біржі
            pair = random.choice(pairs)
            buy_exchange = random.choice(exchanges)
            
            # Вибираємо іншу біржу для продажу
            available_exchanges = [e for e in exchanges if e != buy_exchange]
            sell_exchange = random.choice(available_exchanges)
            
            # Генеруємо ціну купівлі (реалістична для обраної пари)
            base_price = get_realistic_price(pair)
            buy_price = base_price * random.uniform(0.98, 1.0)
            
            # Визначаємо ціну продажу на основі бажаного прибутку
            profit_percent = scenario["profit"]
            sell_price = buy_price * (1 + profit_percent / 100)
            
            # Отримуємо комісії для обраних бірж
            buy_fee = fee_configs[buy_exchange]["buy"]
            sell_fee = fee_configs[sell_exchange]["sell"]
            
            # Розраховуємо чистий прибуток
            buy_with_fee = buy_price * (1 + buy_fee / 100)
            sell_with_fee = sell_price * (1 - sell_fee / 100)
            net_profit_percent = (sell_with_fee - buy_with_fee) / buy_with_fee * 100
            
            opportunity = ArbitrageOpportunity(
                symbol=pair,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                profit_percent=profit_percent,
                buy_fee=buy_fee,
                sell_fee=sell_fee,
                net_profit_percent=net_profit_percent,
                buy_fee_type=config.BUY_FEE_TYPE,
                sell_fee_type=config.SELL_FEE_TYPE
            )
            
            # Додаємо інформаційне повідомлення про тип тесту
            await telegram_worker.send_message(
                f"<b>🧪 Тес
