# main.py
import time
import asyncio
import logging
import signal
import sys
import traceback
from datetime import datetime
import json
import os
from typing import Dict, Any

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
start_time = time.time()
cycle_count = 0
total_opportunities = 0

async def check_arbitrage_opportunities():
    """
    Перевіряє арбітражні можливості та відправляє сповіщення
    """
    global running, telegram_worker, arbitrage_finder, cycle_count, total_opportunities
    
    try:
        # Створюємо директорію для статусу, якщо вона не існує
        os.makedirs("status", exist_ok=True)
        
        # Ініціалізуємо Telegram Worker
        telegram_worker = TelegramWorker(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        await telegram_worker.start()
        
        # Ініціалізуємо пошуковик арбітражних можливостей
        arbitrage_finder = ArbitrageFinder(['binance', 'kucoin', 'kraken'])
        await arbitrage_finder.initialize()
        
        main_logger.info(f"{config.APP_NAME} успішно запущено!")
        
        # Основний цикл роботи
        while running:
            try:
                cycle_count += 1
                main_logger.info(f"Цикл перевірки #{cycle_count} розпочато. Перевіряємо пари: {config.PAIRS}")
                start_cycle_time = time.time()
                
                # Шукаємо арбітражні можливості
                opportunities = await arbitrage_finder.find_opportunities()
                
                # Якщо є можливості, відправляємо повідомлення
                if opportunities:
                    total_opportunities += len(opportunities)
                    main_logger.info(f"Знайдено {len(opportunities)} арбітражних можливостей")
                    for idx, opp in enumerate(opportunities, 1):
                        main_logger.info(f"Відправка арбітражної можливості #{idx}: {opp.symbol} ({opp.profit_percent:.2f}%)")
                        message = opp.to_message()
                        await telegram_worker.send_message(message, parse_mode="HTML")
                else:
                    main_logger.info("Арбітражних можливостей не знайдено")
                
                # Зберігаємо статус у JSON-файл
                await save_status(opportunities)
                    
                cycle_duration = time.time() - start_cycle_time
                main_logger.info(f"Цикл #{cycle_count} завершено за {cycle_duration:.2f} сек. "
                               f"Очікуємо {config.CHECK_INTERVAL} сек.")
                
                # Періодично надсилаємо статус в Telegram (кожні 10 циклів)
                if cycle_count % 10 == 0:
                    await send_status_message()
                
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

async def save_status(opportunities = None):
    """
    Зберігає поточний статус бота у JSON-файл
    """
    global cycle_count, total_opportunities, start_time
    
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)
    
    status_data = {
        "app_name": config.APP_NAME,
        "status": "running" if running else "stopped",
        "version": "2.0.0",
        "uptime": {
            "seconds": uptime_seconds,
            "formatted": f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s"
        },
        "cycles": {
            "total": cycle_count,
            "last_check": datetime.now().isoformat()
        },
        "opportunities": {
            "total_found": total_opportunities,
            "last_check": len(opportunities) if opportunities is not None else 0
        },
        "telegram": await telegram_worker.get_queue_info() if telegram_worker else {"status": "not_initialized"},
        "arbitrage": arbitrage_finder.get_stats() if arbitrage_finder else {"status": "not_initialized"},
        "config": {
            "check_interval": config.CHECK_INTERVAL,
            "min_profit_threshold": config.MIN_PROFIT_THRESHOLD,
            "pairs": config.PAIRS,
            "test_mode": getattr(config, 'TEST_MODE', False)
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Зберігаємо повний статус
    with open("status/status.json", "w") as f:
        json.dump(status_data, f, indent=2)
    
    # Зберігаємо короткий статус для швидкого доступу
    short_status = {
        "status": "running" if running else "stopped",
        "uptime": status_data["uptime"]["formatted"],
        "cycles": cycle_count,
        "opportunities_found": total_opportunities,
        "last_update": datetime.now().isoformat()
    }
    
    with open("status/short_status.json", "w") as f:
        json.dump(short_status, f, indent=2)
    
    return status_data

async def send_status_message():
    """
    Відправляє статус бота в Telegram
    """
    global telegram_worker, cycle_count, total_opportunities, start_time
    
    if not telegram_worker:
        main_logger.error("Неможливо відправити статус - Telegram Worker не ініціалізовано")
        return
    
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    queue_info = await telegram_worker.get_queue_info()
    
    status_message = (
        f"<b>📊 Статус {config.APP_NAME}</b>\n\n"
        f"<b>Стан:</b> {'Працює' if running else 'Зупинено'}\n"
        f"<b>Час роботи:</b> {hours:02d}:{minutes:02d}:{seconds:02d}\n"
        f"<b>Кількість циклів:</b> {cycle_count}\n"
        f"<b>Знайдено арбітражних можливостей:</b> {total_opportunities}\n"
        f"<b>Повідомлень у черзі:</b> {queue_info['queue_size']}\n"
        f"<b>Повідомлень відправлено:</b> {queue_info['messages_sent']}\n"
        f"<b>Поріг прибутку:</b> {config.MIN_PROFIT_THRESHOLD}%\n"
        f"<b>Інтервал перевірки:</b> {config.CHECK_INTERVAL} сек"
    )
    
    await telegram_worker.send_message(status_message, parse_mode="HTML")

async def cleanup():
    """
    Закриває всі ресурси при зупинці програми
    """
    global running
    running = False
    
    main_logger.info(f"Зупинка {config.APP_NAME}...")
    
    # Зберігаємо фінальний статус
    await save_status([])
    
    if arbitrage_finder:
        await arbitrage_finder.close_exchanges()
        
    if telegram_worker:
        # Відправляємо повідомлення про зупинку
        try:
            await telegram_worker.send_message(f"🛑 {config.APP_NAME} зупинено!")
            # Чекаємо, поки повідомлення буде відправлено
            if telegram_worker.queue:
                await telegram_worker.queue.join()
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
    global loop
    
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
