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
            
        # Отримуємо список активних користувачів
        active_users = self.user_manager.get_active_users()
        
        if only_admins:
            # Відправляємо лише адміністраторам
            admin_users = {user_id: user_data for user_id, user_data in active_users.items()
                          if user_data["subscription_type"] == "admin"}
            logger.info(f"Відправка повідомлення {len(admin_users)} адміністраторам")
            users_to_notify = admin_users
        else:
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
            
        # Витягуємо символ (пару) з повідомлення за допомогою регулярного виразу
        symbol_match = re.search(r'<b>Пара:</b> ([^<\n]+)', opportunity_message)
        if not symbol_match:
            logger.error("Не вдалося визначити пару з повідомлення про арбітражну можливість")
            return False
            
        symbol = symbol_match.group(1).strip()
        
        # Отримуємо список активних користувачів
        active_users = self.user_manager.get_active_users()
        
        # Витягуємо відсоток прибутку з повідомлення
        profit_match = re.search(r'Арбітражна можливість \((\d+\.\d+)%\)', opportunity_message)
        if not profit_match:
            logger.error("Не вдалося визначити відсоток прибутку з повідомлення")
            profit_percent = 0.0
        else:
            profit_percent = float(profit_match.group(1))
        
        # Кількість повідомлених користувачів
        notified_count = 0
        
        for user_id, user_data in active_users.items():
            try:
                # Перевіряємо, чи користувача цікавить ця пара
                user_pairs = user_data.get("pairs", [])
                if not user_pairs or symbol not in user_pairs:
                    continue
                    
                # Перевіряємо мінімальний поріг прибутку
                user_min_profit = user_data.get("min_profit", config.DEFAULT_MIN_PROFIT)
                if profit_percent < user_min_profit:
                    continue
                    
                # Отримуємо затримку для цього користувача
                delay = self.user_manager.get_user_notification_delay(user_id)
                
                # Для користувачів із затримкою можна реалізувати логіку затримки
                if delay > 0:
                    logger.debug(f"Затримка повідомлення для користувача {user_id} на {delay} секунд")
                    await asyncio.sleep(delay)
                
                # Відправляємо повідомлення
                await self.send_message(opportunity_message, user_id, parse_mode="HTML")
                
                # Збільшуємо лічильник повідомлень
                self.user_manager.increment_notifications(user_id)
                
                notified_count += 1
                
            except Exception as e:
                logger.error(f"Помилка при відправці повідомлення користувачу {user_id}: {e}")
                
        logger.info(f"Повідомлено {notified_count} користувачів про арбітражну можливість для {symbol}")
        return True
            
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
        Обробляє команди від користувачів
        """
        logger.info("Запущено обробник команд")
        
        while True:
            try:
                # Отримуємо оновлення від Telegram API
                updates = await self.get_updates()
                
                for update in updates:
                    # Обробляємо повідомлення
                    if 'message' in update:
                        await self.process_message(update['message'])
                        
                # Чекаємо перед наступним запитом
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("Обробник команд зупинено")
                break
            except Exception as e:
                logger.error(f"Помилка при обробці команд: {e}")
                # Чекаємо трохи перед повторною спробою
                await asyncio.sleep(5)
                
    async def get_updates(self) -> List[Dict[str, Any]]:
        """
        Отримує оновлення від Telegram API
        """
        if not self.notifier or not self.notifier.session:
            return []
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            
            params = {
                "offset": self.last_update_id + 1,
                "timeout": 30
            }
            
            async with self.notifier.session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if result['ok'] and result['result']:
                        # Оновлюємо last_update_id
                        self.last_update_id = max(update['update_id'] for update in result['result'])
                        return result['result']
                        
                return []
                
        except Exception as e:
            logger.error(f"Помилка при отриманні оновлень від Telegram API: {e}")
            return []
            
    async def process_message(self, message: Dict[str, Any]):
        """
        Обробляє повідомлення від користувача
        """
        if 'text' not in message:
            return
            
        text = message['text']
        chat_id = str(message['chat']['id'])
        username = message['from'].get('username', '')
        first_name = message['from'].get('first_name', '')
        last_name = message['from'].get('last_name', '')
        
        # Оновлюємо або додаємо користувача
        self.user_manager.add_user(chat_id, username, first_name, last_name)
        
        # Обробляємо команди
        if text.startswith('/'):
            command = text.split(' ')[0].lower()
            args = text[len(command):].strip()
            
            await self.handle_command(command, args, chat_id, username, first_name)
    
    async def handle_command(self, command: str, args: str, 
                            chat_id: str, username: str, first_name: str):
        """
        Обробляє команду від користувача
        """
        user_data = self.user_manager.get_user(chat_id)
        if not user_data:
            await self.send_message(
                "Вітаємо! Для початку роботи з ботом використайте команду /start",
                chat_id
            )
            return
        
        # Обробляємо різні команди
        if command == '/start':
            await self.cmd_start(chat_id, first_name)
        elif command == '/help':
            await self.cmd_help(chat_id)
        elif command == '/status':
            await self.cmd_status(chat_id)
        elif command == '/subscribe':
            await self.cmd_subscribe(chat_id)
        elif command == '/unsubscribe':
            await self.cmd_unsubscribe(chat_id)
        elif command == '/pairs':
            await self.cmd_pairs(chat_id, args)
        elif command == '/threshold':
            await self.cmd_threshold(chat_id, args)
        elif command == '/settings':
            await self.cmd_settings(chat_id)
        else:
            # Невідома команда
            await self.send_message(
                f"Невідома команда. Використайте /help для отримання списку доступних команд.",
                chat_id
            )
    
    async def cmd_start(self, chat_id: str, first_name: str):
        """
        Обробляє команду /start
        """
        user_data = self.user_manager.get_user(chat_id)
        
        # Активуємо користувача, якщо він неактивний
        if not user_data["active"]:
            self.user_manager.set_user_active(chat_id, True)
        
        welcome_message = (
            f"Вітаємо, {first_name}! 👋\n\n"
            f"Ласкаво просимо до {config.APP_NAME} - бота для відстеження арбітражних можливостей "
            f"на криптовалютних біржах.\n\n"
            f"Ваша підписка: <b>{config.USER_SUBSCRIPTION_TYPES[user_data['subscription_type']]['description']}</b>\n\n"
            f"Використайте /help для отримання списку доступних команд."
        )
        
        await self.send_message(welcome_message, chat_id, parse_mode="HTML")
    
    async def cmd_help(self, chat_id: str):
        """
        Обробляє команду /help
        """
        commands_list = "\n".join([f"/{cmd} - {desc}" for cmd, desc in config.BOT_COMMANDS.items()])
        
        help_message = (
            f"<b>Довідка по {config.APP_NAME}</b>\n\n"
            f"Доступні команди:\n"
            f"{commands_list}\n\n"
            f"Бот автоматично надсилатиме вам повідомлення про арбітражні можливості "
            f"відповідно до ваших налаштувань.\n\n"
            f"Для зміни налаштувань використовуйте команду /settings."
        )
        
        await self.send_message(help_message, chat_id, parse_mode="HTML")
    
    async def cmd_status(self, chat_id: str):
        """
        Обробляє команду /status
        """
        user_data = self.user_manager.get_user(chat_id)
        
        subscription_type = user_data["subscription_type"]
        subscription_info = config.USER_SUBSCRIPTION_TYPES[subscription_type]
        
        pairs_list = ", ".join(user_data["pairs"]) if user_data["pairs"] else "Не вибрано"
        
        status_message = (
            f"<b>Статус підписки</b>\n\n"
            f"Тип підписки: <b>{subscription_info['description']}</b>\n"
            f"Статус: <b>{'Активний' if user_data['active'] else 'Неактивний'}</b>\n"
            f"Валютні пари: <b>{pairs_list}</b>\n"
            f"Мінімальний поріг прибутку: <b>{user_data['min_profit']}%</b>\n"
            f"Отримано повідомлень: <b>{user_data.get('notifications_count', 0)}</b>\n"
            f"Затримка повідомлень: <b>{subscription_info['notification_delay']} секунд</b>\n"
            f"Максимальна кількість пар: <b>{subscription_info['max_pairs'] if subscription_info['max_pairs'] != -1 else 'Без обмежень'}</b>\n"
        )
        
        await self.send_message(status_message, chat_id, parse_mode="HTML")
    
    async def cmd_subscribe(self, chat_id: str):
        """
        Обробляє команду /subscribe
        """
        self.user_manager.set_user_active(chat_id, True)
        
        await self.send_message(
            "Ви успішно підписалися на повідомлення про арбітражні можливості. "
            "Використайте команду /pairs для вибору валютних пар і /threshold для встановлення "
            "мінімального порогу прибутку.",
            chat_id
        )
    
    async def cmd_unsubscribe(self, chat_id: str):
        """
        Обробляє команду /unsubscribe
        """
        self.user_manager.set_user_active(chat_id, False)
        
        await self.send_message(
            "Ви відписалися від повідомлень про арбітражні можливості. "
            "Використайте команду /subscribe щоб підписатися знову.",
            chat_id
        )
    
    async def cmd_pairs(self, chat_id: str, args: str):
        """
        Обробляє команду /pairs
        """
        user_data = self.user_manager.get_user(chat_id)
        
        if not args:
            # Показуємо поточний список пар
            current_pairs = user_data["pairs"]
            all_pairs = config.PAIRS
            
            pairs_message = "<b>Керування валютними парами</b>\n\n"
            
            if current_pairs:
                pairs_message += "Ваші поточні пари:\n"
                for pair in current_pairs:
                    pairs_message += f"✅ {pair}\n"
            else:
                pairs_message += "У вас не вибрано жодної пари.\n"
                
            pairs_message += "\nДоступні пари:\n"
            for pair in all_pairs:
                if pair not in current_pairs:
                    pairs_message += f"❌ {pair}\n"
                    
            pairs_message += (
                "\nДля додавання або видалення пари використайте команду:\n"
                "/pairs add ПАРА - додати пару\n"
                "/pairs remove ПАРА - видалити пару\n"
                "/pairs reset - скинути список пар\n"
                "/pairs all - додати всі доступні пари\n\n"
                "Приклад: /pairs add BTC/USDT"
            )
            
            await self.send_message(pairs_message, chat_id, parse_mode="HTML")
            return
            
        # Обробляємо команди для додавання/видалення пар
        parts = args.strip().split(' ', 1)
        if len(parts) < 1:
            await self.send_message("Некоректний формат команди. Використайте /pairs для довідки.", chat_id)
            return
            
        subcmd = parts[0].lower()
        
        if subcmd == "reset":
            # Скидаємо список пар
            self.user_manager.update_user_pairs(chat_id, [])
            await self.send_message("Список пар скинуто.", chat_id)
            
        elif subcmd == "all":
            # Додаємо всі пари
            subscription_type = user_data["subscription_type"]
            max_pairs = config.USER_SUBSCRIPTION_TYPES[subscription_type]["max_pairs"]
            
            if max_pairs == -1:  # Без обмежень
                self.user_manager.update_user_pairs(chat_id, config.PAIRS)
                await self.send_message(f"Додано всі доступні пари ({len(config.PAIRS)}).", chat_id)
            else:
                self.user_manager.update_user_pairs(chat_id, config.PAIRS[:max_pairs])
                await self.send_message(
                    f"Додано {min(max_pairs, len(config.PAIRS))} пар (ліміт вашої підписки).",
                    chat_id
                )
                
        elif subcmd == "add" and len(parts) > 1:
            # Додаємо пару
            pair = parts[1].strip().upper()
            
            if pair not in config.PAIRS:
                await self.send_message(f"Пара {pair} не підтримується.", chat_id)
                return
                
            current_pairs = user_data["pairs"]
            if pair in current_pairs:
                await self.send_message(f"Пара {pair} вже додана.", chat_id)
                return
                
            # Перевіряємо ліміт пар
            subscription_type = user_data["subscription_type"]
            max_pairs = config.USER_SUBSCRIPTION_TYPES[subscription_type]["max_pairs"]
            
            if max_pairs != -1 and len(current_pairs) >= max_pairs:
                await self.send_message(
                    f"Ви досягли ліміту пар для вашої підписки ({max_pairs}).",
                    chat_id
                )
                return
                
            # Додаємо пару
            new_pairs = current_pairs + [pair]
            self.user_manager.update_user_pairs(chat_id, new_pairs)
            await self.send_message(f"Пара {pair} додана.", chat_id)
            
        elif subcmd == "remove" and len(parts) > 1:
            # Видаляємо пару
            pair = parts[1].strip().upper()
            
            current_pairs = user_data["pairs"]
            if pair not in current_pairs:
                await self.send_message(f"Пара {pair} не знайдена у вашому списку.", chat_id)
                return
                
            # Видаляємо пару
            new_pairs = [p for p in current_pairs if p != pair]
            self.user_manager.update_user_pairs(chat_id, new_pairs)
            await self.send_message(f"Пара {pair} видалена.", chat_id)
            
        else:
            await self.send_message("Некоректний формат команди. Використайте /pairs для довідки.", chat_id)
    
    async def cmd_threshold(self, chat_id: str, args: str):
        """
        Обробляє команду /threshold
        """
        user_data = self.user_manager.get_user(chat_id)
        
        if not args:
            # Показуємо поточний поріг прибутку
            threshold_message = (
                f"<b>Налаштування порогу прибутку</b>\n\n"
                f"Поточний мінімальний поріг прибутку: <b>{user_data['min_profit']}%</b>\n\n"
                f"Для зміни порогу використайте команду:\n"
                f"/threshold ЗНАЧЕННЯ\n\n"
                f"Приклад: /threshold 1.5"
            )
            
            await self.send_message(threshold_message, chat_id, parse_mode="HTML")
            return
            
        # Обробляємо встановлення нового порогу
        try:
            new_threshold = float(args.strip())
            
            if new_threshold <= 0:
                await self.send_message("Поріг прибутку повинен бути більше 0%.", chat_id)
                return
                
            # Встановлюємо новий поріг
            self.user_manager.set_user_min_profit(chat_id, new_threshold)
            await self.send_message(f"Мінімальний поріг прибутку встановлено на {new_threshold}%.", chat_id)
            
        except ValueError:
            await self.send_message(
                "Некоректне значення. Введіть число, наприклад: /threshold 1.5",
                chat_id
            )
    
    async def cmd_settings(self, chat_id: str):
        """
        Обробляє команду /settings
        """
        user_data = self.user_manager.get_user(chat_id)
        
        subscription_type = user_data["subscription_type"]
        subscription_info = config.USER_SUBSCRIPTION_TYPES[subscription_type]
        
        settings_message = (
            f"<b>Налаштування користувача</b>\n\n"
            f"Тип підписки: <b>{subscription_info['description']}</b>\n"
            f"Статус: <b>{'Активний' if user_data['active'] else 'Неактивний'}</b>\n"
            f"Мінімальний поріг прибутку: <b>{user_data['min_profit']}%</b>\n\n"
            f"Для керування підпискою використовуйте:\n"
            f"/subscribe - підписатися на повідомлення\n"
            f"/unsubscribe - відписатися від повідомлень\n\n"
            f"Для керування валютними парами:\n"
            f"/pairs - керування валютними парами\n\n"
            f"Для зміни порогу прибутку:\n"
            f"/threshold - зміна мінімального порогу прибутку"
        )
        
        await self.send_message(settings_message, chat_id, parse_mode="HTML")
