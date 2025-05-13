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
from arbitrage.triangular_finder import TriangularArbitrageFinder
from exchange_api.factory import ExchangeFactory
from telegram_worker import TelegramWorker

# Отримуємо логер
main_logger = logging.getLogger('main')

# Глобальні змінні для зберігання стану програми
running = True
telegram_worker = None
arbitrage_finder = None
triangular_finders = []  # Зберігатимемо об'єкти пошуковиків трикутного арбітражу

async def check_arbitrage_opportunities():
    """
    Перевіряє арбітражні можливості та відправляє сповіщення
    """
    global running, telegram_worker, arbitrage_finder, triangular_finders
    
    try:
        # Ініціалізуємо Telegram Worker
        telegram_worker = TelegramWorker(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        await telegram_worker.start()
        
        # Ініціалізуємо пошуковик крос-біржових арбітражних можливостей
        arbitrage_finder = ArbitrageFinder(
            ['binance', 'kucoin', 'kraken'],
            min_profit=config.MIN_PROFIT_THRESHOLD,
            include_fees=config.INCLUDE_FEES,
            buy_fee_type=config.BUY_FEE_TYPE,
            sell_fee_type=config.SELL_FEE_TYPE
        )
        await arbitrage_finder.initialize()
        
        # Ініціалізуємо пошуковики трикутного арбітражу для кожної біржі
        exchange_names = ['binance', 'kucoin', 'kraken']
        triangular_finders = []
        
        for exchange_name in exchange_names:
            try:
                # Створюємо об'єкт біржі
                exchange = ExchangeFactory.create(exchange_name)
                
                # Створюємо пошуковик трикутного арбітражу
                triangular_finder = TriangularArbitrageFinder(
                    exchange, 
                    base_currency="USDT",
                    min_profit=config.TRIANGULAR_MIN_PROFIT_THRESHOLD
                )
                
                triangular_finders.append((exchange_name, triangular_finder, exchange))
                main_logger.info(f"Ініціалізовано пошуковик трикутного арбітражу для {exchange_name}")
            except Exception as e:
                main_logger.error(f"Помилка при ініціалізації пошуковика трикутного арбітражу для {exchange_name}: {e}")
        
        fee_status = "з урахуванням комісій" if config.INCLUDE_FEES else "без урахування комісій"
        main_logger.info(f"{config.APP_NAME} успішно запущено ({fee_status}, типи комісій: купівля - {config.BUY_FEE_TYPE}, продаж - {config.SELL_FEE_TYPE})!")
        
        # Відправляємо повідомлення про запуск всім адміністраторам
        admin_message = (
            f"<b>✅ {config.APP_NAME} запущено!</b>\n\n"
            f"<b>Конфігурація:</b>\n"
            f"• Врахування комісій: {'Увімкнено' if config.INCLUDE_FEES else 'Вимкнено'}\n"
            f"• Тип комісій для купівлі: {config.BUY_FEE_TYPE}\n"
            f"• Тип комісій для продажу: {config.SELL_FEE_TYPE}\n"
            f"• Мінімальний поріг прибутку (крос-біржовий): {config.MIN_PROFIT_THRESHOLD}%\n"
            f"• Мінімальний поріг прибутку (трикутний): {config.TRIANGULAR_MIN_PROFIT_THRESHOLD}%\n"
            f"• Біржі: Binance, KuCoin, Kraken\n"
            f"• Валютні пари: {', '.join(config.PAIRS[:5])}...\n"
            f"• Інтервал перевірки: {config.CHECK_INTERVAL} секунд"
        )
        
        # Відправляємо повідомлення адміністраторам
        await telegram_worker.broadcast_message(admin_message, parse_mode="HTML", only_admins=True)
        
        # Основний цикл роботи
        while running:
            try:
                # Шукаємо арбітражні можливості
                main_logger.info(f"Пошук арбітражних можливостей для {len(config.PAIRS)} пар...")
                cross_opportunities = await arbitrage_finder.find_opportunities()
                if cross_opportunities:
                    main_logger.info(f"Знайдено {len(cross_opportunities)} крос-біржових арбітражних можливостей")
                else:
                    main_logger.info("Не знайдено жодної крос-біржової арбітражної можливості")
                
                # Логуємо пошук трикутних можливостей
                main_logger.info("Пошук трикутних арбітражних можливостей...")
                triangular_opportunities_count = 0
                all_opportunities = cross_opportunities.copy() if cross_opportunities else []
                
                # Шукаємо трикутні арбітражні можливості на кожній біржі
                for exchange_name, triangular_finder, exchange in triangular_finders:
                    try:
                        main_logger.info(f"Шукаємо трикутні можливості на {exchange_name}...")
                        triangular_opportunities = await triangular_finder.find_opportunities()
                        if triangular_opportunities:
                            all_opportunities.extend(triangular_opportunities)
                            triangular_opportunities_count += len(triangular_opportunities)
                            main_logger.info(f"Знайдено {len(triangular_opportunities)} трикутних можливостей на {exchange_name}")
                        else:
                            main_logger.info(f"Не знайдено трикутних можливостей на {exchange_name}")
                    except Exception as e:
                        main_logger.error(f"Помилка при пошуку трикутних можливостей на {exchange_name}: {e}")
                        main_logger.error(traceback.format_exc())
                
                # Якщо є можливості, відправляємо повідомлення
                if all_opportunities:
                    main_logger.info(f"Підготовка до відправки повідомлень про {len(all_opportunities)} можливостей...")
                    
                    for index, opp in enumerate(all_opportunities):
                        try:
                            main_logger.info(f"Обробка можливості #{index+1}: {opp.symbol}, {opp.profit_percent:.2f}%")
                            message = opp.to_message()
                            main_logger.debug(f"Сформовано повідомлення для {opp.symbol}")
                            
                            # Надсилаємо повідомлення користувачам
                            delivery_success = await telegram_worker.notify_about_opportunity(message)
                            
                            if delivery_success:
                                main_logger.info(f"Повідомлення про можливість {opp.symbol} успішно надіслано")
                            else:
                                main_logger.warning(f"Не вдалося надіслати повідомлення про можливість {opp.symbol}")
                                
                        except Exception as e:
                            main_logger.error(f"Помилка при обробці можливості {opp.symbol}: {e}")
                            main_logger.error(traceback.format_exc())
                else:
                    main_logger.info("Не знайдено жодної арбітражної можливості")
                
                # Зберігаємо статус у JSON-файл
                status = {
                    "last_check": datetime.now().isoformat(),
                    "opportunities_found": len(all_opportunities),
                    "cross_opportunities": len(cross_opportunities) if 'cross_opportunities' in locals() else 0,
                    "triangular_opportunities": len(all_opportunities) - (len(cross_opportunities) if 'cross_opportunities' in locals() else 0),
                    "running": running,
                    "include_fees": config.INCLUDE_FEES,
                    "buy_fee_type": config.BUY_FEE_TYPE,
                    "sell_fee_type": config.SELL_FEE_TYPE,
                    "active_users": len(telegram_worker.user_manager.get_active_approved_users())
                }
                
                # Якщо є можливості, додаємо їх у статус
                if all_opportunities:
                    status["top_opportunities"] = [opp.to_dict() for opp in all_opportunities[:5]]
                
                # Створюємо директорію для статусу, якщо вона не існує
                status_dir = os.path.dirname("status.json")
                if status_dir and not os.path.exists(status_dir):
                    os.makedirs(status_dir)
                
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
    
    # Закриваємо з'єднання з біржами для трикутного арбітражу
    for _, _, exchange in triangular_finders:
        try:
            await exchange.close()
        except Exception as e:
            main_logger.error(f"Помилка при закритті з'єднання з біржею: {e}")
        
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
        os.makedirs("logs", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        
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
