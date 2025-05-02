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
        buy_fee_type = config.BUY_FEE_TYPE
        sell_fee_type = config.SELL_FEE_TYPE
        main_logger.info(f"{config.APP_NAME} успішно запущено ({fee_status}, тип комісії купівлі: {buy_fee_type}, тип комісії продажу: {sell_fee_type})!")
        
        # Відправляємо додаткову інформацію про конфігурацію
        if config.INCLUDE_FEES:
            config_message = (
                f"<b>ℹ️ Конфігурація {config.APP_NAME}</b>\n\n"
                f"<b>Мінімальний поріг прибутку:</b> {config.MIN_PROFIT_THRESHOLD}%\n"
                f"<b>Врахування комісій:</b> Увімкнено\n"
                f"<b>Тип комісій купівлі:</b> {config.BUY_FEE_TYPE}\n"
                f"<b>Тип комісій продажу:</b> {config.SELL_FEE_TYPE}\n"
                f"<b>Комісії бірж (купівля-{config.BUY_FEE_TYPE}):</b>\n"
                f"   • Binance: {config.EXCHANGE_FEES['binance'][config.BUY_FEE_TYPE]}%\n"
                f"   • KuCoin: {config.EXCHANGE_FEES['kucoin'][config.BUY_FEE_TYPE]}%\n"
                f"   • Kraken: {config.EXCHANGE_FEES['kraken'][config.BUY_FEE_TYPE]}%\n"
                f"<b>Комісії бірж (продаж-{config.SELL_FEE_TYPE}):</b>\n"
                f"   • Binance: {config.EXCHANGE_FEES['binance'][config.SELL_FEE_TYPE]}%\n"
                f"   • KuCoin: {config.EXCHANGE_FEES['kucoin'][config.SELL_FEE_TYPE]}%\n"
                f"   • Kraken: {config.EXCHANGE_FEES['kraken'][config.SELL_FEE_TYPE]}%\n"
                f"<b>Інтервал перевірки:</b> {config.CHECK_INTERVAL} секунд"
            )
            await telegram_worker.send_message(config_message, parse_mode="HTML")
        
        # Основний цикл роботи
        while running:
            try:
                # Шукаємо арбітражні можливості
                opportunities = await arbitrage_finder.find_opportunities()
                
                # Якщо є можливості, відправляємо повідомлення
                for opp in opportunities:
                    message = opp.to_message()
                    await telegram_worker.send_message(message, parse_mode="HTML")
                
                # Зберігаємо статус у JSON-файл
                status = {
                    "last_check": datetime.now().isoformat(),
                    "opportunities_found": len(opportunities),
                    "running": running,
                    "include_fees": config.INCLUDE_FEES,
                    "buy_fee_type": config.BUY_FEE_TYPE,
                    "sell_fee_type": config.SELL_FEE_TYPE
                }
                
                # Переконаємося, що директорія status існує
                os.makedirs("status", exist_ok=True)
                
                with open("status/current.json", "w") as f:
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
        # Створюємо директорії для логів та статусу
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
