# test_runner.py
import asyncio
import logging
import sys
import random
import os
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
        pairs = config.PAIRS  # Використовуємо пари з конфігурації
        exchanges = ["Binance", "KuCoin", "Kraken"]
        
        for _ in range(3):
            pair = random.choice(pairs)
            buy_exchange = random.choice(exchanges)
            
            # Вибираємо іншу біржу для продажу
            available_exchanges = [e for e in exchanges if e != buy_exchange]
            sell_exchange = random.choice(available_exchanges)
            
            # Генеруємо ціни з хорошою арбітражною можливістю
            buy_price = random.uniform(10, 50000)
            profit_percent = random.uniform(1.0, 5.0)
            sell_price = buy_price * (1 + profit_percent / 100)
            
            # Додаємо комісії для тестування
            buy_fee = config.EXCHANGE_FEES[buy_exchange.lower()][config.BUY_FEE_TYPE]
            sell_fee = config.EXCHANGE_FEES[sell_exchange.lower()][config.SELL_FEE_TYPE]
            
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
            
            # Відправляємо форматоване повідомлення про арбітражну можливість
            await telegram_worker.send_message(
                opportunity.to_message(),
                parse_mode="HTML"
            )
            
            # Чекаємо 2 секунди між повідомленнями
            await asyncio.sleep(2)
        
        # Чекаємо, поки всі повідомлення будуть відправлені
        await telegram_worker.queue.join()
        
        # Відправляємо повідомлення про завершення тесту
        await telegram_worker.send_message("✅ Тест успішно завершено")
        
        # Знову чекаємо на відправку останнього повідомлення
        await telegram_worker.queue.join()
        
        test_logger.info("Тест успішно завершено")
        
    except Exception as e:
        test_logger.error(f"Помилка під час тесту: {e}")
    finally:
        # Зупиняємо Telegram Worker
        await telegram_worker.stop()

if __name__ == "__main__":
    try:
        # Створюємо директорії для логів
        os.makedirs(os.path.dirname(config.MAIN_LOG_FILE), exist_ok=True)
        
        # Зберігаємо час початку тесту
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_logger.info(f"Початок тестування {config.APP_NAME} о {start_time}")
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_telegram_notifications())
        
        # Зберігаємо час завершення тесту
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_logger.info(f"Завершення тестування {config.APP_NAME} о {end_time}")
    except KeyboardInterrupt:
        test_logger.info("Тест зупинено користувачем")
    except Exception as e:
        test_logger.error(f"Критична помилка під час тесту: {e}")
    finally:
        if loop and not loop.is_closed():
            loop.close()
