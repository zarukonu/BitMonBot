# telegram_worker.py
import asyncio
import logging
import time
import re
import json
from typing import Optional, Dict, List, Any, Tuple
import aiohttp
import traceback
from datetime import datetime

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
        self.health_check_task: Optional[asyncio.Task] = None
        self.last_update_id = 0
        self.user_manager = UserManager()
        self.running = True
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """
        Запускає воркер
        """
        # Створюємо чергу повідомлень
        self.queue = asyncio.Queue()
        
        # Створюємо HTTP сесію
        self.session = aiohttp.ClientSession()
        
        # Створюємо нотифікатор
        self.notifier = TelegramNotifier(self.bot_token, self.admin_chat_id, self.queue)
        await self.notifier.initialize()
        
        # Запускаємо обробник черги
        self.worker_task = asyncio.create_task(self.notifier.process_queue())
        
        # Запускаємо моніторинг черги
        self.monitor_task = asyncio.create_task(self.monitor_queue())
        
        # Запускаємо обробник команд
        self.command_handler_task = asyncio.create_task(self.handle_commands())
        
        # Запускаємо перевірку стану бота
        self.health_check_task = asyncio.create_task(self.health_check())
        
        # Відправляємо повідомлення про старт бота
        await self.notifier.send_formatted_message(config.START_MESSAGE)
        
        logger.info("Telegram Worker успішно запущено")
        
    async def stop(self):
        """
        Зупиняє воркер
        """
        logger.info("Зупинка Telegram Worker...")
        
        self.running = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.health_check_task = None
        
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
            
        if self.session:
            await self.session.close()
            self.session = None
            
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
        
        while self.running:
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
                logger.error(traceback.format_exc())
                # Чекаємо трохи перед повторною спробою
                await asyncio.sleep(5)
                
    async def handle_commands(self):
        """
        Обробляє команди від користувачів через Telegram API
        """
        logger.info("Запущено обробник команд Telegram")
        
        # Базовий URL для Telegram Bot API
        base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        while self.running:
            try:
                # Отримуємо оновлення
                url = f"{base_url}/getUpdates?offset={self.last_update_id + 1}&timeout=30"
                
                if not self.session:
                    logger.warning("HTTP сесія не ініціалізована, створюємо нову")
                    self.session = aiohttp.ClientSession()
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("ok") and data.get("result"):
                            updates = data["result"]
                            
                            if updates:
                                logger.info(f"Отримано {len(updates)} нових повідомлень")
                                
                                for update in updates:
                                    # Оновлюємо last_update_id
                                    if update["update_id"] > self.last_update_id:
                                        self.last_update_id = update["update_id"]
                                    
                                    await self._process_update(update)
                    else:
                        logger.error(f"Помилка при отриманні оновлень: {response.status}")
                        logger.error(f"Відповідь: {await response.text()}")
                
                # Невелика затримка між запитами, щоб уникнути надмірного навантаження
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("Обробник команд зупинено")
                break
            except Exception as e:
                logger.error(f"Помилка при обробці команд: {e}")
                logger.error(traceback.format_exc())
                # Чекаємо трохи перед повторною спробою
                await asyncio.sleep(5)
    
    async def _process_update(self, update):
        """
        Обробляє одне оновлення від Telegram
        """
        try:
            # Логуємо отримане оновлення для діагностики
            logger.debug(f"Отримано оновлення: {json.dumps(update)}")
            
            if "message" in update and "text" in update["message"]:
                message = update["message"]
                chat_id = str(message["chat"]["id"])
                text = message["text"]
                user_id = str(message["from"]["id"])
                username = message["from"].get("username", "")
                first_name = message["from"].get("first_name", "")
                last_name = message["from"].get("last_name", "")
                
                logger.info(f"Отримано повідомлення від {user_id} ({username}): {text}")
                
                # Додаємо або оновлюємо користувача
                self.user_manager.add_user(user_id, username, first_name, last_name)
                
                # Обробляємо команди
                if text.startswith('/'):
                    command = text.split()[0].lower()
                    args = text.split()[1:] if len(text.split()) > 1 else []
                    
                    if command == '/start':
                        await self._handle_start_command(chat_id, user_id)
                    elif command == '/help':
                        await self._handle_help_command(chat_id)
                    elif command == '/status':
                        await self._handle_status_command(chat_id, user_id)
                    elif command == '/pairs':
                        await self._handle_pairs_command(chat_id, user_id, args)
                    elif command == '/threshold':
                        await self._handle_threshold_command(chat_id, user_id, args)
                    elif command == '/approve' and user_id in config.ADMIN_USER_IDS:
                        await self._handle_admin_approve_command(chat_id, user_id, args)
                    elif command == '/block' and user_id in config.ADMIN_USER_IDS:
                        await self._handle_admin_block_command(chat_id, user_id, args)
                    elif command == '/users' and user_id in config.ADMIN_USER_IDS:
                        await self._handle_admin_users_command(chat_id)
                    else:
                        await self.send_message(
                            f"Невідома команда: {command}\nВикористайте /help для перегляду доступних команд",
                            chat_id
                        )
                else:
                    # Звичайне повідомлення
                    await self._handle_regular_message(chat_id, user_id, text)
                
            elif "callback_query" in update:
                # Обробка натискань на інлайн-кнопки
                callback_query = update["callback_query"]
                query_id = callback_query["id"]
                chat_id = str(callback_query["message"]["chat"]["id"])
                user_id = str(callback_query["from"]["id"])
                data = callback_query["data"]
                
                logger.info(f"Отримано callback query від {user_id}: {data}")
                
                # Обробляємо різні типи callback query
                if data.startswith("pair_"):
                    await self._handle_pair_selection(query_id, chat_id, user_id, data)
                elif data.startswith("threshold_"):
                    await self._handle_threshold_selection(query_id, chat_id, user_id, data)
                else:
                    # Якщо не знаємо, як обробити callback query, просто відправляємо порожню відповідь
                    await self._answer_callback_query(query_id)
        
        except Exception as e:
            logger.error(f"Помилка при обробці оновлення: {e}")
            logger.error(traceback.format_exc())
    
    async def _answer_callback_query(self, query_id, text=None, show_alert=False):
        """
        Відповідає на callback query
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
            data = {"callback_query_id": query_id}
            
            if text:
                data["text"] = text
                
            if show_alert:
                data["show_alert"] = True
                
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    logger.error(f"Помилка при відповіді на callback query: {response.status}")
                    logger.error(f"Відповідь: {await response.text()}")
        except Exception as e:
            logger.error(f"Помилка при відповіді на callback query: {e}")

    async def _handle_start_command(self, chat_id, user_id):
        """
        Обробляє команду /start
        """
        welcome_message = (
            f"👋 Вітаємо у {config.APP_NAME}!\n\n"
            f"Цей бот допоможе вам знаходити арбітражні можливості на криптовалютних біржах.\n\n"
            f"Використовуйте команду /help щоб дізнатися більше про доступні команди."
        )
        
        await self.send_message(welcome_message, chat_id)
        logger.info(f"Відправлено привітальне повідомлення користувачу {user_id}")

    async def _handle_help_command(self, chat_id):
        """
        Обробляє команду /help
        """
        help_message = "📚 <b>Доступні команди:</b>\n\n"
        
        for command, description in config.BOT_COMMANDS.items():
            help_message += f"{command} - {description}\n"
        
        await self.send_message(help_message, chat_id, parse_mode="HTML")

    async def _handle_status_command(self, chat_id, user_id):
        """
        Обробляє команду /status
        """
        user = self.user_manager.get_user(user_id)
        
        if not user:
            await self.send_message("⚠️ Ваш профіль не знайдено. Будь ласка, використайте команду /start для реєстрації.", chat_id)
            return
        
        status_message = (
            f"<b>📊 Ваш статус:</b>\n\n"
            f"<b>ID:</b> {user_id}\n"
            f"<b>Активний:</b> {'✅' if user.get('active', False) else '❌'}\n"
            f"<b>Схвалений:</b> {'✅' if user.get('is_approved', False) else '❌'}\n"
            f"<b>Підписки на пари:</b> {len(user.get('pairs', []))}\n"
            f"<b>Мінімальний прибуток:</b> {user.get('min_profit', config.DEFAULT_MIN_PROFIT)}%\n"
            f"<b>Отримано повідомлень:</b> {user.get('notifications_count', 0)}\n"
        )
        
        # Додаємо інформацію про активні пари
        pairs = user.get('pairs', [])
        if pairs:
            status_message += "\n<b>Активні пари:</b>\n"
            for i, pair in enumerate(pairs[:10], 1):
                status_message += f"{i}. {pair}\n"
                
            if len(pairs) > 10:
                status_message += f"...та ще {len(pairs) - 10}\n"
        
        await self.send_message(status_message, chat_id, parse_mode="HTML")

    async def _handle_pairs_command(self, chat_id, user_id, args):
        """
        Обробляє команду /pairs для керування підписками на валютні пари
        """
        user = self.user_manager.get_user(user_id)
        
        if not user:
            await self.send_message("⚠️ Ваш профіль не знайдено. Будь ласка, використайте команду /start для реєстрації.", chat_id)
            return
        
        # Якщо є аргументи, то це можуть бути пари для додавання/видалення
        if args:
            action = args[0].lower()
            
            if action == "add" and len(args) > 1:
                # Додаємо пари
                pairs_to_add = [pair.upper() for pair in args[1:]]
                valid_pairs = [pair for pair in pairs_to_add if pair in config.ALL_PAIRS]
                
                if valid_pairs:
                    # Отримуємо поточні пари користувача
                    user_pairs = user.get('pairs', [])
                    
                    # Додаємо нові пари
                    for pair in valid_pairs:
                        if pair not in user_pairs:
                            user_pairs.append(pair)
                    
                    # Оновлюємо пари користувача
                    self.user_manager.update_user_pairs(user_id, user_pairs)
                    
                    await self.send_message(
                        f"✅ Додано {len(valid_pairs)} пар до ваших підписок.\n\n"
                        f"Використайте /status щоб переглянути ваші поточні підписки.",
                        chat_id
                    )
                else:
                    await self.send_message(
                        f"⚠️ Жодної валідної пари не знайдено серед {len(args[1:])} вказаних.\n\n"
                        f"Доступні пари: {', '.join(config.ALL_PAIRS[:5])}...\n"
                        f"Використайте /pairs без аргументів для перегляду всіх доступних пар.",
                        chat_id
                    )
            
            elif action == "remove" and len(args) > 1:
                # Видаляємо пари
                pairs_to_remove = [pair.upper() for pair in args[1:]]
                
                # Отримуємо поточні пари користувача
                user_pairs = user.get('pairs', [])
                
                # Видаляємо вказані пари
                removed_count = 0
                for pair in pairs_to_remove:
                    if pair in user_pairs:
                        user_pairs.remove(pair)
                        removed_count += 1
                
                # Оновлюємо пари користувача
                self.user_manager.update_user_pairs(user_id, user_pairs)
                
                await self.send_message(
                    f"✅ Видалено {removed_count} пар з ваших підписок.\n\n"
                    f"Використайте /status щоб переглянути ваші поточні підписки.",
                    chat_id
                )
            
            elif action == "all":
                # Підписуємо на всі пари
                self.user_manager.update_user_pairs(user_id, config.ALL_PAIRS[:])
                
                await self.send_message(
                    f"✅ Ви підписані на всі {len(config.ALL_PAIRS)} доступних пар.\n\n"
                    f"Використайте /status щоб переглянути ваші поточні підписки.",
                    chat_id
                )
            
            elif action == "clear":
                # Очищаємо всі підписки
                self.user_manager.update_user_pairs(user_id, [])
                
                await self.send_message(
                    "✅ Всі підписки видалено.\n\n"
                    "Використайте /pairs all щоб підписатися на всі доступні пари.",
                    chat_id
                )
            
            else:
                # Невідома дія
                await self.send_message(
                    "⚠️ Невідома дія. Доступні дії:\n"
                    "/pairs add PAIR1 PAIR2 ... - додати пари\n"
                    "/pairs remove PAIR1 PAIR2 ... - видалити пари\n"
                    "/pairs all - підписатися на всі пари\n"
                    "/pairs clear - видалити всі підписки\n"
                    "/pairs - переглянути доступні пари",
                    chat_id
                )
        
        else:
            # Без аргументів виводимо список доступних пар
            pairs_message = "<b>📊 Доступні пари:</b>\n\n"
            
            # Групуємо пари за першою валютою
            pairs_by_base = {}
            for pair in config.ALL_PAIRS:
                base, quote = pair.split('/')
                if base not in pairs_by_base:
                    pairs_by_base[base] = []
                pairs_by_base[base].append(pair)
            
            # Виводимо пари по групах
            for base, pairs in sorted(pairs_by_base.items()):
                pairs_message += f"<b>{base}:</b> {', '.join(pairs)}\n"
            
            pairs_message += "\nДля керування підписками використовуйте:\n"
            pairs_message += "/pairs add PAIR1 PAIR2 ... - додати пари\n"
            pairs_message += "/pairs remove PAIR1 PAIR2 ... - видалити пари\n"
            pairs_message += "/pairs all - підписатися на всі пари\n"
            pairs_message += "/pairs clear - видалити всі підписки\n"
            
            await self.send_message(pairs_message, chat_id, parse_mode="HTML")

    async def _handle_threshold_command(self, chat_id, user_id, args):
        """
        Обробляє команду /threshold для встановлення мінімального порогу прибутку
        """
        user = self.user_manager.get_user(user_id)
        
        if not user:
            await self.send_message("⚠️ Ваш профіль не знайдено. Будь ласка, використайте команду /start для реєстрації.", chat_id)
            return
        
        # Якщо є аргументи, то це може бути новий поріг
        if args:
            try:
                new_threshold = float(args[0])
                
                # Перевіряємо чи поріг у допустимих межах
                if new_threshold < 0.1:
                    await self.send_message("⚠️ Поріг не може бути меншим за 0.1%", chat_id)
                    return
                
                if new_threshold > 10.0:
                    await self.send_message("⚠️ Поріг не може бути більшим за 10.0%", chat_id)
                    return
                
                # Встановлюємо новий поріг
                self.user_manager.set_user_min_profit(user_id, new_threshold)
                
                await self.send_message(
                    f"✅ Встановлено новий мінімальний поріг прибутку: {new_threshold}%\n\n"
                    f"Тепер ви будете отримувати сповіщення лише про можливості з прибутком не менше {new_threshold}%.",
                    chat_id
                )
                
            except ValueError:
                await self.send_message(
                    "⚠️ Невірний формат порогу. Використайте число з десятковою крапкою, наприклад: /threshold 0.8",
                    chat_id
                )
        
        else:
            # Без аргументів виводимо поточний поріг і пропонуємо варіанти
            current_threshold = user.get('min_profit', config.DEFAULT_MIN_PROFIT)
            
            threshold_message = (
                f"<b>📊 Поточний мінімальний поріг прибутку:</b> {current_threshold}%\n\n"
                f"Ви можете встановити новий поріг, наприклад:\n"
                f"/threshold 0.5 - для отримання сповіщень про можливості з прибутком від 0.5%\n"
                f"/threshold 1.0 - для отримання сповіщень про можливості з прибутком від 1.0%\n"
            )
            
            await self.send_message(threshold_message, chat_id, parse_mode="HTML")

    async def _handle_admin_approve_command(self, chat_id, admin_id, args):
        """
        Обробляє команду /approve для схвалення користувача (лише для адміністраторів)
        """
        if not args:
            await self.send_message("⚠️ Потрібно вказати ID користувача для схвалення", chat_id)
            return
        
        user_id = args[0]
        user = self.user_manager.get_user(user_id)
        
        if not user:
            await self.send_message(f"⚠️ Користувача з ID {user_id} не знайдено", chat_id)
            return
        
        # Схвалюємо користувача
        self.user_manager.approve_user(user_id)
        
        await self.send_message(f"✅ Користувача {user_id} схвалено", chat_id)
        
        # Також повідомляємо користувача про схвалення
        try:
            await self.send_message(
                "✅ Ваш обліковий запис схвалено адміністратором!\n"
                "Тепер ви будете отримувати сповіщення про арбітражні можливості.",
                user_id
            )
        except Exception as e:
            logger.error(f"Помилка при відправці повідомлення користувачу {user_id}: {e}")

    async def _handle_admin_block_command(self, chat_id, admin_id, args):
        """
        Обробляє команду /block для блокування користувача (лише для адміністраторів)
        """
        if not args:
            await self.send_message("⚠️ Потрібно вказати ID користувача для блокування", chat_id)
            return
        
        user_id = args[0]
        user = self.user_manager.get_user(user_id)
        
        if not user:
            await self.send_message(f"⚠️ Користувача з ID {user_id} не знайдено", chat_id)
            return
        
        # Блокуємо користувача
        self.user_manager.block_user(user_id)
        
        await self.send_message(f"✅ Користувача {user_id} заблоковано", chat_id)
        
        # Також повідомляємо користувача про блокування
        try:
            await self.send_message(
                "❌ Ваш обліковий запис заблоковано адміністратором.\n"
                "Ви більше не будете отримувати сповіщення про арбітражні можливості.",
                user_id
            )
        except Exception as e:
            logger.error(f"Помилка при відправці повідомлення користувачу {user_id}: {e}")

    async def _handle_admin_users_command(self, chat_id):
        """
        Обробляє команду /users для перегляду списку користувачів (лише для адміністраторів)
        """
        # Отримуємо різні категорії користувачів
        all_users = self.user_manager.get_all_users()
        active_users = self.user_manager.get_active_approved_users()
        pending_users = self.user_manager.get_pending_users()
        admin_users = self.user_manager.get_admin_users()
        
        users_message = (
            f"<b>👥 Статистика користувачів:</b>\n\n"
            f"<b>Всього користувачів:</b> {len(all_users)}\n"
            f"<b>Активних схвалених:</b> {len(active_users)}\n"
            f"<b>Очікують схвалення:</b> {len(pending_users)}\n"
            f"<b>Адміністраторів:</b> {len(admin_users)}\n\n"
        )
        
        # Додаємо інформацію про користувачів, які очікують схвалення
        if pending_users:
            users_message += "<b>Користувачі, які очікують схвалення:</b>\n"
            for user_id, user_data in pending_users.items():
                username = user_data.get('username', '')
                first_name = user_data.get('first_name', '')
                last_name = user_data.get('last_name', '')
                
                user_info = f"{user_id}"
                if username:
                    user_info += f" (@{username})"
                if first_name or last_name:
                    user_info += f" - {first_name} {last_name}"
                
                users_message += f"{user_info}\n"
                users_message += f"  /approve {user_id} - схвалити | /block {user_id} - заблокувати\n"
        
        await self.send_message(users_message, chat_id, parse_mode="HTML")

    async def _handle_regular_message(self, chat_id, user_id, text):
        """
        Обробляє звичайне повідомлення
        """
        # Перевіряємо статус користувача
        user = self.user_manager.get_user(user_id)
        
        if not user or not user.get('is_approved', False):
            # Якщо користувач не схвалений, повідомляємо про це
            await self.send_message(
                "⚠️ Ваш обліковий запис ще не схвалено.\n"
                "Будь ласка, зачекайте на схвалення адміністратором або зв'яжіться з ним для прискорення процесу.",
                chat_id
            )
            
            # Сповіщаємо адміністраторів про нового користувача
            for admin_id in config.ADMIN_USER_IDS:
                try:
                    await self.send_message(
                        f"👤 Новий користувач очікує схвалення:\n\n"
                        f"ID: {user_id}\n"
                        f"Ім'я: {user.get('first_name', '')} {user.get('last_name', '')}\n"
                        f"Логін: {user.get('username', 'відсутній')}\n\n"
                        f"Для схвалення: /approve {user_id}\n"
                        f"Для блокування: /block {user_id}",
                        admin_id
                    )
                except Exception as e:
                    logger.error(f"Помилка при сповіщенні адміністратора {admin_id}: {e}")
            
            return
        
        # Оновлюємо активність користувача
        self.user_manager.update_user_activity(user_id)
        
        # Відповідаємо на повідомлення
        response = (
            "Я розумію тільки команди, які починаються з символу /\n"
            "Використайте /help, щоб дізнатися про доступні команди."
        )
        
        await self.send_message(response, chat_id)

    async def _handle_pair_selection(self, query_id, chat_id, user_id, data):
        """
        Обробляє вибір пари через інлайн-кнопку
        """
        # Відповідаємо на callback query, щоб зникло "годинник" на кнопці
        await self._answer_callback_query(query_id)
        
        # Отримуємо пару з data
        pair = data.replace("pair_", "")
        
        # Отримуємо поточні пари користувача
        user = self.user_manager.get_user(user_id)
        if not user:
            await self.send_message("⚠️ Ваш профіль не знайдено", chat_id)
            return
        
        user_pairs = user.get('pairs', [])
        
        # Якщо пара вже є в списку, видаляємо її, інакше додаємо
        if pair in user_pairs:
            user_pairs.remove(pair)
            action = "видалено з"
        else:
            user_pairs.append(pair)
            action = "додано до"
        
        # Оновлюємо пари користувача
        self.user_manager.update_user_pairs(user_id, user_pairs)
        
        await self.send_message(f"✅ Пару {pair} {action} ваших підписок", chat_id)

    async def _handle_threshold_selection(self, query_id, chat_id, user_id, data):
        """
        Обробляє вибір порогу через інлайн-кнопку
        """
        # Відповідаємо на callback query, щоб зникло "годинник" на кнопці
        await self._answer_callback_query(query_id)
        
        # Отримуємо поріг з data
        threshold_str = data.replace("threshold_", "")
        
        try:
            threshold = float(threshold_str)
            
            # Встановлюємо новий поріг
            self.user_manager.set_user_min_profit(user_id, threshold)
            
            await self.send_message(f"✅ Встановлено новий мінімальний поріг прибутку: {threshold}%", chat_id)
            
        except ValueError:
            await self.send_message("⚠️ Невірний формат порогу", chat_id)

    async def health_check(self):
        """
        Періодично перевіряє стан Telegram воркера
        """
        logger.info("Запущено перевірку стану Telegram Worker")
        
        while self.running:
            try:
                # Перевіряємо з'єднання з Telegram API
                if self.session:
                    url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
                    try:
                        async with self.session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data.get("ok"):
                                    logger.debug("З'єднання з Telegram API успішне")
                                else:
                                    logger.warning(f"Помилка API Telegram: {data.get('description', 'Невідома помилка')}")
                            else:
                                logger.warning(f"Помилка з'єднання з Telegram API: {response.status}")
                    except Exception as e:
                        logger.error(f"Помилка при перевірці з'єднання з Telegram API: {e}")
                        logger.error(traceback.format_exc())
                        # Спробуємо створити нову сесію
                        try:
                            if self.session:
                                await self.session.close()
                            self.session = aiohttp.ClientSession()
                            logger.info("Створено нову HTTP сесію")
                        except Exception as session_error:
                            logger.error(f"Помилка при створенні нової HTTP сесії: {session_error}")
                else:
                    logger.warning("HTTP сесія не ініціалізована, створюємо нову")
                    self.session = aiohttp.ClientSession()
                
                # Логуємо статус бота для моніторингу
                now = datetime.now()
                logger.info(f"Telegram Worker активний. Час: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Зберігаємо час останньої перевірки в статус-файл для моніторингу
                try:
                    telegram_status = {
                        "last_check": now.isoformat(),
                        "running": self.running,
                        "queue_size": self.queue.qsize() if self.queue else 0
                    }
                    
                    os.makedirs("status", exist_ok=True)
                    with open("status/telegram_status.json", "w") as f:
                        json.dump(telegram_status, f, indent=4)
                except Exception as e:
                    logger.error(f"Помилка при збереженні статусу Telegram Worker: {e}")
                
                # Чекаємо до наступної перевірки
                await asyncio.sleep(300)  # Перевірка кожні 5 хвилин
                
            except asyncio.CancelledError:
                logger.info("Перевірку стану Telegram Worker зупинено")
                break
            except Exception as e:
                logger.error(f"Помилка при перевірці стану Telegram Worker: {e}")
                logger.error(traceback.format_exc())
                # Чекаємо трохи перед повторною спробою
                await asyncio.sleep(60)
