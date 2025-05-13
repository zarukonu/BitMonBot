# test_opportunity.py
import asyncio
import logging
import sys
from datetime import datetime

import config
import logger
from telegram_worker import TelegramWorker
from arbitrage.opportunity import ArbitrageOpportunity
from user_manager import UserManager

# Отримуємо логер
test_logger = logging.getLogger('main')

async def test_opportunity_notification():
    """
    Тестує відправку повідомлення про арбітражну можливість
    """
    telegram_worker = TelegramWorker(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    
    try:
        # Запускаємо Telegram Worker
        await telegram_worker.start()
        
        test_logger.info("Тест повідомлень про арбітражні можливості розпочато")
        
        # Відправляємо стартове повідомлення адміністратору
        await telegram_worker.send_message(
            "🔍 Запущено тест повідомлень про арбітражні можливості.",
            config.TELEGRAM_CHAT_ID
        )
        
        # Створюємо тестову арбітражну можливість з прибутком 0.6%
        opportunity = ArbitrageOpportunity(
            symbol="BTC/USDT",
            buy_exchange="Binance",
            sell_exchange="Kraken",
            buy_price=40000.0,
            sell_price=40240.0,  # ~0.6% прибутку
            profit_percent=0.6,
            buy_fee=0.1,  # 0.1% комісія на Binance (taker)
            sell_fee=0.26,  # 0.26% комісія на Kraken (taker)
            net_profit_percent=0.24,  # 0.6% - комісії
            buy_fee_type="taker",
            sell_fee_type="taker"
        )
        
        # Перевіряємо наявність користувачів
        user_manager = UserManager()
        active_users = user_manager.get_active_approved_users()
        test_logger.info(f"Знайдено {len(active_users)} активних схвалених користувачів")
        
        # Логуємо інформацію про користувачів для діагностики
        for user_id, user_data in active_users.items():
            pairs = user_data.get("pairs", [])
            min_profit = user_data.get("min_profit", config.DEFAULT_MIN_PROFIT)
            test_logger.info(f"Користувач {user_id}: {len(pairs)} пар, мін. прибуток {min_profit}%")
            
            # Якщо користувач підписаний на BTC/USDT, логуємо детальніше
            if "BTC/USDT" in pairs:
                test_logger.info(f"Користувач {user_id} підписаний на BTC/USDT!")
            
        # Генеруємо повідомлення
        message = opportunity.to_message()
        test_logger.info(f"Сформовано тестове повідомлення про можливість: {opportunity.symbol}, {opportunity.profit_percent}%")
        
        # 1. Пряма відправка адміністратору
        test_logger.info("Тест 1: Пряма відправка адміністратору")
        await telegram_worker.send_message(
            f"📊 ТЕСТ: Пряма відправка адміністратору:\n\n{message}",
            config.TELEGRAM_CHAT_ID,
            parse_mode="HTML"
        )
        test_logger.info(f"Пряме повідомлення адміністратору надіслано")
        
        # Невелика пауза між відправками
        await asyncio.sleep(2)
        
        # 2. Спроба відправки через метод notify_about_opportunity
        test_logger.info("Тест 2: Відправка через notify_about_opportunity")
        notification_result = await telegram_worker.notify_about_opportunity(message)
        test_logger.info(f"Результат notify_about_opportunity: {notification_result}")
        
        # 3. Тест із спеціально сформованим повідомленням без форматування
        test_logger.info("Тест 3: Повідомлення без HTML-форматування")
        simple_message = (
            f"🔍 Арбітражна можливість (0.6%)\n\n"
            f"Пара: BTC/USDT\n"
            f"Купити на: Binance за 40000.00000000\n"
            f"Продати на: Kraken за 40240.00000000\n"
            f"Прибуток: 0.60%\n"
            f"Час: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        simple_result = await telegram_worker.notify_about_opportunity(simple_message)
        test_logger.info(f"Результат простого повідомлення: {simple_result}")
        
        # 4. Перевірка broadcast_message
        test_logger.info("Тест 4: Відправка через broadcast_message")
        broadcast_result = await telegram_worker.broadcast_message(
            "📢 ТЕСТ: Широкомовне повідомлення для всіх користувачів",
            parse_mode="HTML"
        )
        test_logger.info(f"Результат broadcast_message: {broadcast_result}")
        
        # Чекаємо, поки всі повідомлення будуть відправлені
        await telegram_worker.queue.join()
        test_logger.info("Всі повідомлення в черзі оброблено")
        
        # Підсумкове повідомлення
        await telegram_worker.send_message(
            "✅ Тестування повідомлень завершено!",
            config.TELEGRAM_CHAT_ID
        )
        
    except Exception as e:
        test_logger.error(f"Помилка під час тесту: {e}")
        import traceback
        test_logger.error(traceback.format_exc())
    finally:
        # Зупиняємо Telegram Worker
        await telegram_worker.stop()

if __name__ == "__main__":
    try:
        # Налаштування консольного логування для тесту
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Додаємо консольний обробник до всіх логерів
        for logger_name in ['main', 'telegram', 'arbitrage', 'users']:
            log = logging.getLogger(logger_name)
            log.addHandler(console_handler)
            log.setLevel(logging.INFO)
            
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_opportunity_notification())
    except KeyboardInterrupt:
        test_logger.info("Тест зупинено користувачем")
    except Exception as e:
        test_logger.error(f"Критична помилка під час тесту: {e}")
        import traceback
        test_logger.error(traceback.format_exc())
    finally:
        if loop and not loop.is_closed():
            loop.close()
