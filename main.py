# main.py
import asyncio
import logging
import signal
import sys
import traceback
from datetime import datetime, timezone
import json
import os

import config
import logger
from arbitrage.finder import ArbitrageFinder
from arbitrage.triangular_finder import TriangularArbitrageFinder
from arbitrage.pair_analyzer import ArbitragePairAnalyzer
from telegram_worker import TelegramWorker
from web_server import start_web_server

# Отримуємо логер
main_logger = logging.getLogger('main')

# Глобальні змінні для зберігання стану програми
running = True
telegram_worker = None
arbitrage_finder = None
triangular_finder = None
pair_analyzer = None
web_dashboard = None

async def check_arbitrage_opportunities():
    """
    Перевіряє арбітражні можливості та відправляє сповіщення
    """
    global running, telegram_worker, arbitrage_finder, triangular_finder, pair_analyzer, web_dashboard
    
    try:
        # Створюємо необхідні директорії
        os.makedirs("logs", exist_ok=True)
        os.makedirs("status", exist_ok=True)
        
        # Ініціалізуємо Telegram Worker
        telegram_worker = TelegramWorker(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        await telegram_worker.start()
        
        # Ініціалізуємо пошуковик арбітражних можливостей
        arbitrage_finder = ArbitrageFinder(['binance', 'kucoin', 'kraken'])
        await arbitrage_finder.initialize()
        
        # Перевірка успішної ініціалізації бірж
        if 'binance' not in arbitrage_finder.exchanges:
            main_logger.warning("Біржу Binance не було ініціалізовано, трикутний арбітраж неможливий")
        else:
            # Ініціалізуємо пошуковик трикутних арбітражних можливостей на Binance
            triangular_finder = TriangularArbitrageFinder(
                arbitrage_finder.exchanges['binance']
            )
        
        # Ініціалізуємо аналізатор пар
        pair_analyzer = ArbitragePairAnalyzer()
        
        # Запускаємо веб-сервер, якщо він увімкнений в конфігурації
        web_dashboard = await start_web_server()
        
        main_logger.info(f"{config.APP_NAME} v{config.VERSION} успішно запущено!")
        
        # Основний цикл роботи
        while running:
            try:
                # Визначаємо поточний час
                now = datetime.now().replace(tzinfo=timezone.utc)
                current_hour = now.hour
                
                # Перевіряємо, чи зараз пікові години для арбітражу
                is_peak_time = any(start <= current_hour < end for start, end in config.PEAK_HOURS)
                
                # Встановлюємо інтервал перевірки залежно від часу
                check_interval = config.PEAK_CHECK_INTERVAL if is_peak_time else config.REGULAR_CHECK_INTERVAL
                
                main_logger.info(f"Початок перевірки арбітражних можливостей. Режим: {'пікові години' if is_peak_time else 'звичайний'}")
                
                # Виконуємо пошук крос-біржових можливостей
                cross_opportunities = await arbitrage_finder.find_opportunities()
                main_logger.info(f"Знайдено {len(cross_opportunities)} крос-біржових можливостей")
                
                # Виконуємо пошук трикутних можливостей на Binance, якщо біржа доступна
                triangular_opportunities = []
                if triangular_finder:
                    triangular_opportunities = await triangular_finder.find_opportunities()
                    main_logger.info(f"Знайдено {len(triangular_opportunities)} трикутних можливостей")
                
                # Об'єднуємо можливості
                all_opportunities = cross_opportunities + triangular_opportunities
                
                # Оновлюємо статистику пар, якщо знайдено можливості
                if all_opportunities:
                    await pair_analyzer.update_stats(all_opportunities)
                
                # Сортуємо за чистим прибутком
                all_opportunities.sort(key=lambda x: x.net_profit_percent, reverse=True)
                
                # Відправляємо сповіщення про найкращі можливості
                for opp in all_opportunities[:5]:  # Відправляємо повідомлення лише про топ-5 можливостей
                    message = opp.to_message()
                    await telegram_worker.send_message(message, parse_mode="HTML")
                
                # Зберігаємо статус
                status = {
                    "last_check": now.isoformat(),
                    "is_peak_time": is_peak_time,
                    "check_interval": check_interval,
                    "opportunities_found": len(all_opportunities),
                    "top_opportunities": [opp.to_dict() for opp in all_opportunities[:10]],
                    "running": running,
                    "version": config.VERSION
                }
                
                with open("status.json", "w") as f:
                    json.dump(status, f, indent=2)
                
                # Чекаємо до наступної перевірки
                main_logger.info(f"Перевірка завершена. Наступна перевірка через {check_interval} секунд")
                await asyncio.sleep(check_interval)
                
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
    
    if web_dashboard:
        await web_dashboard.stop()
    
    if arbitrage_finder:
        await arbitrage_finder.close_exchanges()
        
    if telegram_worker:
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
    # Отримуємо event loop
    loop = asyncio.get_event_loop()
    
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
        # Створюємо необхідні директорії
        os.makedirs("logs", exist_ok=True)
        os.makedirs("status", exist_ok=True)
        
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
