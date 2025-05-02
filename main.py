# main.py
import asyncio
import logging
import signal
import sys
import traceback
from datetime import datetime
import json
import os
import time

import config
import logger
from arbitrage.finder import ArbitrageFinder
from telegram_worker import TelegramWorker

# Отримуємо логер
main_logger = logging.getLogger('main')

# Змінні для зберігання стану програми
running = True
telegram_worker = None
arbitrage_finder = None

# Створюємо директорію для статусу, якщо вона не існує
os.makedirs('status', exist_ok=True)

async def check_arbitrage_opportunities(loop):
    """
    Перевіряє арбітражні можливості та відправляє сповіщення
    
    Args:
        loop (asyncio.AbstractEventLoop): Цикл подій asyncio
    """
    global running, telegram_worker, arbitrage_finder
    
    try:
        # Ініціалізуємо Telegram Worker
        telegram_worker = TelegramWorker(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        await telegram_worker.start()
        
        # Ініціалізуємо пошуковик арбітражних можливостей
        main_logger.info("Ініціалізація з'єднань з біржами...")
        start_time = time.time()
        arbitrage_finder = ArbitrageFinder(['binance', 'kucoin', 'kraken'])
        await arbitrage_finder.initialize()
        init_time = time.time() - start_time
        main_logger.info(f"Ініціалізацію завершено за {init_time:.2f} секунд")
        
        main_logger.info(f"{config.APP_NAME} успішно запущено!")
        
        # Змінні для статистики
        total_checks = 0
        total_opportunities = 0
        start_time = time.time()
        
        # Основний цикл роботи
        while running:
            try:
                # Шукаємо арбітражні можливості
                check_start = time.time()
                opportunities = await arbitrage_finder.find_opportunities()
                check_time = time.time() - check_start
                
                # Оновлюємо статистику
                total_checks += 1
                total_opportunities += len(opportunities)
                
                # Якщо є можливості, відправляємо повідомлення
                for opp in opportunities:
                    message = opp.to_message()
                    await telegram_worker.send_message(message, parse_mode="HTML")
                
                # Зберігаємо статус у JSON-файли
                current_time = datetime.now()
                
                # Детальний статус
                detailed_status = {
                    "last_check": current_time.isoformat(),
                    "opportunities_found": len(opportunities),
                    "running": running,
                    "uptime": time.time() - start_time,
                    "total_checks": total_checks,
                    "total_opportunities": total_opportunities,
                    "avg_check_time": check_time,
                    "last_opportunities": [opp.to_dict() for opp in opportunities][:5]
                }
                
                # Короткий статус
                status = {
                    "last_check": current_time.isoformat(),
                    "opportunities_found": len(opportunities),
                    "running": running,
                    "uptime": time.time() - start_time,
                    "total_checks": total_checks,
                    "total_opportunities": total_opportunities
                }
                
                # Зберігаємо статуси
                with open("status/detailed_status.json", "w") as f:
                    json.dump(detailed_status, f, indent=2)
                
                with open("status.json", "w") as f:
                    json.dump(status, f, indent=2)
                
                # Логуємо інформацію про перевірку
                if len(opportunities) > 0:
                    main_logger.info(f"Знайдено {len(opportunities)} арбітражних можливостей за {check_time:.2f} секунд")
                else:
                    main_logger.debug(f"Перевірку завершено за {check_time:.2f} секунд, арбітражних можливостей не знайдено")
                
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
    
    try:
        if arbitrage_finder:
            await arbitrage_finder.close_exchanges()
    except Exception as e:
        main_logger.error(f"Помилка при закритті з'єднань з біржами: {e}")
    
    try:
        if telegram_worker:
            # Відправляємо повідомлення про зупинку
            await telegram_worker.send_message(f"🛑 {config.APP_NAME} зупинено!", parse_mode="HTML")
            # Чекаємо, щоб повідомлення було відправлено
            if telegram_worker.queue:
                await telegram_worker.queue.join()
            await telegram_worker.stop()
    except Exception as e:
        main_logger.error(f"Помилка при зупинці Telegram Worker: {e}")
    
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
    # Отримуємо поточний цикл подій
    loop = asyncio.get_running_loop()
    
    # Налаштовуємо обробники сигналів
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await check_arbitrage_opportunities(loop)
    except Exception as e:
        main_logger.error(f"Неочікувана помилка в main(): {e}")
        main_logger.error(traceback.format_exc())
    finally:
        await cleanup()

if __name__ == "__main__":
    try:
        # Створюємо директорію для статусу
        os.makedirs('status', exist_ok=True)
        # Запускаємо цикл подій
        asyncio.run(main())
    except KeyboardInterrupt:
        main_logger.info("Програму зупинено користувачем")
    except Exception as e:
        main_logger.error(f"Критична помилка: {e}")
        main_logger.error(traceback.format_exc())
