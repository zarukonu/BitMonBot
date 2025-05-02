# main.py
import asyncio
import logging
import signal
import sys
import traceback
from datetime import datetime
import json
import os

import config
import logger
from arbitrage.finder import ArbitrageFinder
from telegram_worker import TelegramWorker

# Отримуємо логер
main_logger = logging.getLogger('main')

# Глобальні змінні для зберігання стану програми
running = True
telegram_worker = None
arbitrage_finder = None

async def check_arbitrage_opportunities():
    """
    Перевіряє арбітражні можливості та відправляє сповіщення
    """
    global running, telegram_worker, arbitrage_finder
    
    try:
        # Ініціалізуємо Telegram Worker
        telegram_worker = TelegramWorker(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        await telegram_worker.start()
        
        # Ініціалізуємо пошуковик арбітражних можливостей
        arbitrage_finder = ArbitrageFinder(
            ['binance', 'kucoin', 'kraken'],
            min_profit=config.MIN_PROFIT_THRESHOLD,
            include_fees=config.INCLUDE_FEES,
            buy_fee_type=config.BUY_FEE_TYPE,
            sell_fee_type=config.SELL_FEE_TYPE
        )
        await arbitrage_finder.initialize()
        
        fee_status = "з урахуванням комісій" if config.INCLUDE_FEES else "без урахування комісій"
        main_logger.info(f"{config.APP_NAME} успішно запущено ({fee_status}, типи комісій: купівля - {config.BUY_FEE_TYPE}, продаж - {config.SELL_FEE_TYPE})!")
        
        # Відправляємо повідомлення про запуск всім адміністраторам
        admin_message = (
            f"<b>✅ {config.APP_NAME} запущено!</b>\n\n"
            f"<b>Конфігурація:</b>\n"
            f"• Врахування комісій: {'Увімкнено' if config.INCLUDE_FEES else 'Вимкнено'}\n"
            f"• Тип комісій для купівлі: {config.BUY_FEE_TYPE}\n"
            f"• Тип комісій для продажу: {config.SELL_FEE_TYPE}\n"
            f"• Мінімальний поріг прибутку: {config.MIN_PROFIT_THRESHOLD}%\n"
            f"• Біржі: Binance, KuCoin, Kraken\n"
            f"• Валютні пари: {', '.join(config.PAIRS[:5])}...\n"
            f"• Інтервал перевірки: {config.CHECK_INTERVAL} секунд"
        )
        
        # Відправляємо повідомлення тільки адміністраторам
        await telegram_worker.broadcast_message(admin_message, parse_mode="HTML", only_admins=True)
        
        # Основний цикл роботи
        while running:
            try:
                # Шукаємо арбітражні можливості
                opportunities = await arbitrage_finder.find_opportunities()
                
                # Якщо є можливості, відправляємо повідомлення всім активним користувачам
                for opp in opportunities:
                    message = opp.to_message()
                    
                    # Надсилаємо повідомлення користувачам за підпискою
                    await telegram_worker.notify_about_opportunity(message)
                
                # Зберігаємо статус у JSON-файл
                status = {
                    "last_check": datetime.now().isoformat(),
                    "opportunities_found": len(opportunities),
                    "running": running,
                    "include_fees": config.INCLUDE_FEES,
                    "buy_fee_type": config.BUY_FEE_TYPE,
                    "sell_fee_type": config.SELL_FEE_TYPE,
                    "active_users": len(telegram_worker.user_manager.get_active_users())
                }
                
                with open("status.json", "w") as f:
                    json.dump(status, f, indent=4)
                
                # Чекаємо до наступної перевірки
                await asyncio.sleep(config.CHECK_INTERVAL)
                
            except Exception as e:
                main_logger.error(f"Помилка в основному циклі: {e}")
                main_logger.error(traceback.format_exc())
                # Чекаємо трохи перед повторною спробою
                await asyncio.sleep(10)
                
    except Exception as e:
        main_logger.error(f"Критична помилка при запуску: {e}")
        main_logger.error(traceback.format_exc())
    finally:
        # Закриваємо всі ресурси
        await cleanup()

async def cleanup():
    """
    Закриває всі ресурси при зупинці програми
    """
    main_logger.info(f"Зупинка {config.APP_NAME}...")
    
    if arbitrage_finder:
        await arbitrage_finder.close_exchanges()
        
    if telegram_worker:
        # Повідомляємо адміністраторів про зупинку
        try:
            await telegram_worker.broadcast_message(
                f"<b>🛑 {config.APP_NAME} зупинено!</b>",
                parse_mode="HTML",
                only_admins=True
            )
        except Exception as e:
            main_logger.error(f"Помилка при відправці повідомлення про зупинку: {e}")
            
        await telegram_worker.stop()
        
    main_logger.info(f"{config.APP_NAME} успішно зупинено")

def signal_handler():
    """
    Обробник сигналів переривання
    """
    global running
    running = False
    main_logger.info("Отримано сигнал на зупинку...")

async def main():
    """
    Головна функція програми
    """
    # Налаштовуємо обробники сигналів
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await check_arbitrage_opportunities()
    except Exception as e:
        main_logger.error(f"Неочікувана помилка в main(): {e}")
        main_logger.error(traceback.format_exc())
    finally:
        await cleanup()

if __name__ == "__main__":
    try:
        # Створюємо директорію для логів, якщо вона не існує
        os.makedirs(os.path.dirname(config.MAIN_LOG_FILE), exist_ok=True)
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        main_logger.info("Програму зупинено користувачем")
    except Exception as e:
        main_logger.error(f"Критична помилка: {e}")
        main_logger.error(traceback.format_exc())
    finally:
        if loop and not loop.is_closed():
            loop.close()
