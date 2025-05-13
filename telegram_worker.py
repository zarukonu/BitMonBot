# telegram_worker.py
import asyncio
import logging
import time
import re
from typing import Optional, Dict, List, Any, Tuple
import config
from notifier.telegram_notifier import TelegramNotifier
from user_manager import UserManager

logger = logging.getLogger('telegram')
users_logger = logging.getLogger('users')

class TelegramWorker:
    """
    Воркер для асинхронної обробки черги Telegram-повідомлень
    та обробки команд від користувачів
    """
    def __init__(self, bot_token: str, admin_chat_id: str):
        self.bot_token = bot_token
        self.admin_chat_id = admin_chat_id
        self.queue: Optional[asyncio.Queue] = None
        self.notifier: Optional[TelegramNotifier] = None
        self.worker_task: Optional[asyncio.Task] = None
        self.monitor_task: Optional[asyncio.Task] = None
        self.command_handler_task: Optional[asyncio.Task] = None
        self.last_update_id = 0
        self.user_manager = UserManager()
        
    async def start(self):
        """
        Запускає воркер
        """
        # Створюємо чергу повідомлень
        self.queue = asyncio.Queue()
        
        # Створюємо нотифікатор
        self.notifier = TelegramNotifier(self.bot_token, self.admin_chat_id, self.queue)
        await self.notifier.initialize()
        
        # Запускаємо обробник черги
        self.worker_task = asyncio.create_task(self.notifier.process_queue())
        
        # Запускаємо моніторинг черги
        self.monitor_task = asyncio.create_task(self.monitor_queue())
        
        # Запускаємо обробник команд
        self.command_handler_task = asyncio.create_task(self.handle_commands())
        
        # Відправляємо повідомлення про старт бота
        await self.notifier.send_formatted_message(config.START_MESSAGE)
        
        logger.info("Telegram Worker успішно запущено")
        
    async def stop(self):
        """
        Зупиняє воркер
        """
        logger.info("Зупинка Telegram Worker...")
        
        if self.command_handler_task:
            self.command_handler_task.cancel()
            try:
                await self.command_handler_task
            except asyncio.CancelledError:
                pass
            self.command_handler_task = None
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        # Чекаємо завершення відправки всіх повідомлень
        if self.queue:
            try:
                # Встановлюємо таймаут на 5 секунд
                await asyncio.wait_for(self.queue.join(), timeout=5)
                logger.info("Всі повідомлення у черзі оброблено")
            except asyncio.TimeoutError:
                logger.warning(f"Не всі повідомлення було відправлено. Залишилось {self.queue.qsize()} повідомлень")
            
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
            
        if self.notifier:
            await self.notifier.close()
            self.notifier = None
            
        logger.info("Telegram Worker успішно зупинено")
        
    async def send_message(self, message: str, chat_id: Optional[str] = None, parse_mode: Optional[str] = None):
        """
        Додає повідомлення до черги на відправку
        """
        if not self.notifier:
            logger.error("Спроба відправити повідомлення, але Telegram Worker не запущено")
            return False
            
        # Якщо не вказано chat_id, використовуємо ID адміністратора
        if chat_id is None:
            chat_id = self.admin_chat_id
            
        if parse_mode:
            return await self.notifier.send_formatted_message(message, chat_id, parse_mode)
        else:
            return await self.notifier.send_message(message, chat_id)
            
    async def broadcast_message(self, message: str, parse_mode: Optional[str] = None, 
                               only_admins: bool = False):
        """
        Відправляє повідомлення всім активним користувачам
        """
        if not self.notifier:
            logger.error("Спроба відправити повідомлення, але Telegram Worker не запущено")
            return False
            
        if only_admins:
            # Відправляємо лише адміністраторам
            admin_users = self.user_manager.get_admin_users()
            logger.info(f"Відправка повідомлення {len(admin_users)} адміністраторам")
            users_to_notify = admin_users
        else:
            # Відправляємо всім схваленим користувачам
            active_users = self.user_manager.get_active_approved_users()
            logger.info(f"Відправка повідомлення {len(active_users)} активним користувачам")
            users_to_notify = active_users
            
        # Відправляємо повідомлення всім вибраним користувачам
        for user_id, user_data in users_to_notify.items():
            try:
                await self.send_message(message, user_id, parse_mode)
                # Збільшуємо лічильник повідомлень
                self.user_manager.increment_notifications(user_id)
            except Exception as e:
                logger.error(f"Помилка при відправці повідомлення користувачу {user_id}: {e}")
                
        return True
            
    async def notify_about_opportunity(self, opportunity_message: str):
        """
        Повідомляє користувачів про арбітражну можливість
        """
        if not self.notifier:
            logger.error("Спроба відправити повідомлення, але Telegram Worker не запущено")
            return False
            
        # Виправлений регулярний вираз для знаходження пари
        symbol_match = re.search(r'<b>Пара:</b>\s*([^<\n]+)', opportunity_message)
        
        # Якщо в повідомленні немає поля "Пара", спробуємо знайти "Шлях" (для трикутного арбітражу)
        if not symbol_match:
            symbol_match = re.search(r'<b>Шлях:</b>\s*([^<\n]+)', opportunity_message)
            
        if not symbol_match:
            logger.error(f"Не вдалося визначити пару/шлях з повідомлення: {opportunity_message}")
            # Спроба повідомити про помилку адміністратору
            await self.send_message(
                f"❌ Помилка: не вдалося визначити пару з повідомлення про арбітражну можливість.\n\n"
                f"Повідомлення:\n{opportunity_message}",
                chat_id=self.admin_chat_id
            )
            return False
            
        symbol = symbol_match.group(1).strip()
        logger.info(f"Обробка можливості для пари/шляху: {symbol}")
        
        # Оновлений регулярний вираз для знаходження відсотка прибутку
        # Це враховує різні формати повідомлень з emoji
        profit_match = re.search(r'можливість\s*\((\d+\.\d+)%\)', opportunity_message)
        if not profit_match:
            profit_match = re.search(r'Прибуток:\s*(\d+\.\d+)%', opportunity_message)
            
        if not profit_match:
            logger.error(f"Не вдалося визначити відсоток прибутку з повідомлення: {opportunity_message}")
            profit_percent = 1.0  # Встановлюємо за замовчуванням достатній прибуток щоб повідомлення відправилося
        else:
            profit_percent = float(profit_match.group(1))
        
        logger.info(f"Виявлено арбітражну можливість: {symbol} з прибутком {profit_percent}%")
        
        # Отримуємо список активних схвалених користувачів
        active_users = self.user_manager.get_active_approved_users()
        logger.info(f"Знайдено {len(active_users)} активних схвалених користувачів")
        
        # Для трикутного арбітражу або специфічних шляхів
        # Розбиваємо symbol на складові: може бути "BTC/USDT" або "USDT -> BTC -> ETH -> USDT"
        symbol_parts = [part.strip() for part in re.split(r'[/\->]', symbol)]
        
        # Кількість повідомлених користувачів
        notified_count = 0
        skipped_count = 0
        
        for user_id, user_data in active_users.items():
            try:
                # Отримуємо список пар користувача
                user_pairs = user_data.get("pairs", [])
                logger.debug(f"Користувач {user_id} підписаний на {len(user_pairs)} пар: {user_pairs}")
                
                # Перевіряємо, чи користувача цікавить ця пара
                # 1. Пряма перевірка повного символу
                found_match = symbol in user_pairs
                
                # 2. Перевірка для компонентів символу (для трикутних шляхів)
                if not found_match and "/" not in symbol:
                    # Перевіряємо, чи є хоч одна з криптовалют у парах користувача
                    for part in symbol_parts:
                        if part and any(part in pair for pair in user_pairs):
                            found_match = True
                            break
                
                if not found_match:
                    logger.debug(f"Користувач {user_id} не підписаний на пару {symbol}. Його пари: {user_pairs}")
                    skipped_count += 1
                    continue
                
                # Перевіряємо мінімальний поріг прибутку
                user_min_profit = user_data.get("min_profit", config.DEFAULT_MIN_PROFIT)
                if profit_percent < user_min_profit:
                    logger.debug(f"Прибуток {profit_percent}% менший за поріг користувача {user_id} ({user_min_profit}%)")
                    skipped_count += 1
                    continue
                
                # Відправляємо повідомлення
                logger.info(f"Відправка повідомлення про можливість {symbol} користувачу {user_id}")
                try:
                    await self.send_message(opportunity_message, user_id, parse_mode="HTML")
                    # Збільшуємо лічильник повідомлень
                    self.user_manager.increment_notifications(user_id)
                    notified_count += 1
                    logger.info(f"Повідомлення успішно надіслано користувачу {user_id}")
                except Exception as e:
                    logger.error(f"Помилка при відправці повідомлення користувачу {user_id}: {e}")
            except Exception as e:
                logger.error(f"Помилка при обробці користувача {user_id}: {e}")
                
        # Також відправляємо повідомлення адміністратору
        if notified_count == 0:
            logger.warning(f"Жодного користувача не повідомлено про арбітражну можливість для {symbol}")
            await self.send_message(
                f"⚠️ Повідомлення про арбітражну можливість для {symbol} не надіслано жодному користувачу.\n"
                f"Пропущено {skipped_count} користувачів.",
                chat_id=self.admin_chat_id
            )
        else:
            logger.info(f"Повідомлено {notified_count} користувачів про арбітражну можливість для {symbol} (пропущено {skipped_count})")
            await self.send_message(
                f"✅ Повідомлення про арбітражну можливість для {symbol} надіслано {notified_count} користувачам.",
                chat_id=self.admin_chat_id
            )
            
        return notified_count > 0
            
    async def monitor_queue(self):
        """
        Моніторить стан черги повідомлень
        """
        logger.info("Запущено моніторинг черги повідомлень")
        
        while True:
            try:
                # Логуємо розмір черги
                if self.queue and self.queue.qsize() > 5:
                    logger.warning(f"У черзі накопичилось {self.queue.qsize()} повідомлень!")
                
                # Чекаємо до наступної перевірки
                await asyncio.sleep(30)  # Перевірка кожні 30 секунд
                
            except asyncio.CancelledError:
                logger.info("Моніторинг черги зупинено")
                break
            except Exception as e:
                logger.error(f"Помилка при моніторингу черги: {e}")
                # Чекаємо трохи перед повторною спробою
                await asyncio.sleep(5)
                
    async def handle_commands(self):
        """
        Обробляє команди від користувачів через Telegram API
        """
        logger.info("Запущено обробник команд Telegram")
        
        # Простий цикл обробки команд
        while True:
            try:
                # У повній реалізації тут був би код для отримання і обробки команд від Telegram
                # Для цього тестового варіанту, ми просто чекаємо і нічого не робимо
                await asyncio.sleep(60)  # Перевірка кожну хвилину
                
            except asyncio.CancelledError:
                logger.info("Обробник команд зупинено")
                break
            except Exception as e:
                logger.error(f"Помилка при обробці команд: {e}")
                # Чекаємо трохи перед повторною спробою
                await asyncio.sleep(5)
