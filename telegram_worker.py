# telegram_worker.py
import asyncio
import logging
from typing import Dict, List, Optional, Any
import json
import traceback

import config
from notifier.telegram_notifier import TelegramNotifier

logger = logging.getLogger('telegram')

class TelegramWorker:
    """
    Воркер для асинхронної обробки черги Telegram-повідомлень
    """
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.queue: Optional[asyncio.Queue] = None
        self.notifier: Optional[TelegramNotifier] = None
        self.worker_task: Optional[asyncio.Task] = None
        self.command_handlers: Dict[str, Any] = {}
        self.last_update_id: int = 0
        self.command_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """
        Запускає воркер
        """
        # Створюємо чергу повідомлень
        self.queue = asyncio.Queue()
        
        # Створюємо нотифікатор
        self.notifier = TelegramNotifier(self.bot_token, self.chat_id, self.queue)
        await self.notifier.initialize()
        
        # Запускаємо обробник черги
        self.worker_task = asyncio.create_task(self.notifier.process_queue())
        
        # Запускаємо обробник команд
        self.command_task = asyncio.create_task(self.process_commands())
        
        # Встановлюємо команди бота
        await self.setup_commands()
        
        # Відправляємо повідомлення про старт бота
        await self.notifier.send_formatted_message(config.START_MESSAGE)
        
        logger.info("Telegram Worker успішно запущено")
        
    async def stop(self):
        """
        Зупиняє воркер
        """
        logger.info("Зупинка Telegram Worker...")
        
        if self.command_task:
            self.command_task.cancel()
            try:
                await self.command_task
            except asyncio.CancelledError:
                pass
            self.command_task = None
        
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
        
    async def send_message(self, message: str, parse_mode: Optional[str] = None):
        """
        Додає повідомлення до черги на відправку
        """
        if not self.notifier:
            logger.error("Спроба відправити повідомлення, але Telegram Worker не запущено")
            return False
            
        if parse_mode:
            return await self.notifier.send_formatted_message(message, parse_mode)
        else:
            return await self.notifier.send_message(message)
    
    async def setup_commands(self):
        """
        Налаштовує команди Telegram-бота
        """
        commands = [
            {"command": "start", "description": "Запустити бота"},
            {"command": "stop", "description": "Зупинити бота"},
            {"command": "status", "description": "Отримати статус бота"},
            {"command": "stats", "description": "Статистика арбітражу"},
            {"command": "top", "description": "Найкращі арбітражні пари"}
        ]
        
        # Реєструємо обробники команд
        self.command_handlers = {
            "start": self.handle_start_command,
            "stop": self.handle_stop_command,
            "status": self.handle_status_command,
            "stats": self.handle_stats_command,
            "top": self.handle_top_command
        }
        
        # Відправляємо команди в Telegram API
        if self.notifier and self.notifier.session:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/setMyCommands"
                async with self.notifier.session.post(url, json={"commands": commands}) as response:
                    if response.status == 200:
                        logger.info("Команди бота успішно встановлено")
                    else:
                        response_text = await response.text()
                        logger.error(f"Помилка при встановленні команд бота: {response.status} - {response_text}")
            except Exception as e:
                logger.error(f"Виняток при встановленні команд бота: {e}")
    
    async def process_commands(self):
        """
        Обробляє команди від користувача
        """
        if not self.notifier or not self.notifier.session:
            logger.error("Спроба обробити команди, але Telegram Worker не запущено")
            return
            
        while True:
            try:
                # Отримуємо оновлення
                url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
                params = {
                    "offset": self.last_update_id + 1,
                    "timeout": 30
                }
                
                async with self.notifier.session.post(url, json=params) as response:
                    if response.status == 200:
                        updates = await response.json()
                        
                        if updates.get("ok", False) and "result" in updates:
                            for update in updates["result"]:
                                # Оновлюємо last_update_id
                                self.last_update_id = max(self.last_update_id, update.get("update_id", 0))
                                
                                # Обробляємо команду
                                if "message" in update and "text" in update["message"]:
                                    text = update["message"]["text"]
                                    chat_id = update["message"]["chat"]["id"]
                                    
                                    if text.startswith("/"):
                                        command = text[1:].split(" ")[0]
                                        await self.handle_command(command, chat_id)
                    else:
                        response_text = await response.text()
                        logger.error(f"Помилка при отриманні оновлень: {response.status} - {response_text}")
                
                # Чекаємо 5 секунд перед наступною перевіркою
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                logger.info("Обробник команд зупинено")
                break
            except Exception as e:
                logger.error(f"Помилка при обробці команд: {e}")
                traceback.print_exc()
                await asyncio.sleep(10)  # Збільшуємо затримку у випадку помилки
    
    async def handle_command(self, command: str, chat_id: str):
        """
        Обробляє команду від користувача
        
        Args:
            command (str): Команда
            chat_id (str): ID чату
        """
        logger.info(f"Отримано команду: {command} від чату {chat_id}")
        
        # Перевіряємо, чи команда від дозволеного чату
        if str(chat_id) != self.chat_id:
            logger.warning(f"Отримано команду від недозволеного чату: {chat_id}")
            return
            
        # Викликаємо обробник команди
        handler = self.command_handlers.get(command)
        if handler:
            try:
                await handler()
            except Exception as e:
                logger.error(f"Помилка при обробці команди {command}: {e}")
                await self.send_message(f"❌ Помилка при обробці команди: {e}", parse_mode="HTML")
        else:
            await self.send_message(f"⚠️ Невідома команда: {command}", parse_mode="HTML")
    
    async def handle_start_command(self):
        """
        Обробляє команду /start
        """
        global running
        running = True
        await self.send_message("🚀 Бот запущено і активно шукає арбітражні можливості!", parse_mode="HTML")
    
    async def handle_stop_command(self):
        """
        Обробляє команду /stop
        """
        global running
        running = False
        await self.send_message("🛑 Бот зупинено. Для відновлення роботи використайте команду /start", parse_mode="HTML")
    
    async def handle_status_command(self):
        """
        Обробляє команду /status
        """
        try:
            status_info = {}
            
            # Завантажуємо статус з файлу, якщо він є
            if os.path.exists("status.json"):
                with open("status.json", "r") as f:
                    status_info = json.load(f)
            
            # Форматуємо повідомлення
            message = "<b>📊 Статус бота</b>\n\n"
            
            if status_info:
                # Загальна інформація
                message += f"<b>Версія:</b> {config.VERSION}\n"
                message += f"<b>Стан:</b> {'🟢 Активний' if status_info.get('running', False) else '🔴 Зупинено'}\n"
                
                # Час останньої перевірки
                last_check = status_info.get('last_check', '')
                if last_check:
                    try:
                        last_check_dt = datetime.fromisoformat(last_check)
                        last_check_str = last_check_dt.strftime('%Y-%m-%d %H:%M:%S')
                        message += f"<b>Остання перевірка:</b> {last_check_str}\n"
                    except:
                        message += f"<b>Остання перевірка:</b> {last_check}\n"
                
                # Інформація про інтервал перевірки
                check_interval = status_info.get('check_interval', config.CHECK_INTERVAL)
                is_peak_time = status_info.get('is_peak_time', False)
                message += f"<b>Інтервал перевірки:</b> {check_interval}с {'(пікові години)' if is_peak_time else ''}\n"
                
                # Інформація про знайдені можливості
                opps_found = status_info.get('opportunities_found', 0)
                message += f"<b>Знайдено можливостей:</b> {opps_found}\n"
                
                # Показуємо топ можливості, якщо є
                top_opps = status_info.get('top_opportunities', [])
                if top_opps:
                    message += "\n<b>Топ можливості:</b>\n"
                    for i, opp in enumerate(top_opps[:3], 1):
                        symbol = opp.get('symbol', 'невідомо')
                        profit = opp.get('net_profit_percent', 0)
                        buy_ex = opp.get('buy_exchange', '')
                        sell_ex = opp.get('sell_exchange', '')
                        
                        if opp.get('opportunity_type') == 'triangular':
                            path = opp.get('path', [])
                            path_str = ' → '.join(path) if path else 'невідомо'
                            message += f"{i}. <b>{buy_ex}:</b> {path_str} ({profit:.2f}%)\n"
                        else:
                            message += f"{i}. <b>{symbol}:</b> {buy_ex} → {sell_ex} ({profit:.2f}%)\n"
            else:
                message += "Немає доступної інформації про статус бота."
            
            await self.send_message(message, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Помилка при обробці команди status: {e}")
            await self.send_message(f"❌ Помилка при отриманні статусу: {e}", parse_mode="HTML")
    
    async def handle_stats_command(self):
        """
        Обробляє команду /stats
        """
        try:
            from arbitrage.pair_analyzer import ArbitragePairAnalyzer
            analyzer = ArbitragePairAnalyzer()
            
            message = "<b>📈 Статистика арбітражу</b>\n\n"
            
            # Загальна статистика
            total_opportunities = sum(stats.get('count', 0) for stats in analyzer.pair_stats.values())
            if total_opportunities > 0:
                avg_profit = sum(stats.get('total_net_profit', 0) for stats in analyzer.pair_stats.values()) / total_opportunities
                
                message += f"<b>Всього можливостей:</b> {total_opportunities}\n"
                message += f"<b>Середній чистий прибуток:</b> {avg_profit:.2f}%\n\n"
                
                # Статистика за типами
                cross_count = sum(1 for stats in analyzer.pair_stats.values() if stats.get('opportunity_type') == 'cross')
                triangular_count = sum(1 for stats in analyzer.pair_stats.values() if stats.get('opportunity_type') == 'triangular')
                
                message += f"<b>Крос-біржових можливостей:</b> {cross_count}\n"
                message += f"<b>Трикутних можливостей:</b> {triangular_count}\n"
                
                # Найкращі пари/шляхи
                top_cross = analyzer.get_top_pairs(3, "cross")
                top_triangular = analyzer.get_top_pairs(3, "triangular")
                
                if top_cross:
                    message += "\n<b>Найкращі крос-біржові пари:</b>\n"
                    for i, stats in enumerate(top_cross, 1):
                        symbol = stats.get('symbol', 'невідомо')
                        buy_ex = stats.get('buy_exchange', '')
                        sell_ex = stats.get('sell_exchange', '')
                        avg_net = stats.get('avg_net_profit', 0)
                        count = stats.get('count', 0)
                        
                        message += f"{i}. <b>{symbol}:</b> {buy_ex} → {sell_ex} "
                        message += f"(срд. {avg_net:.2f}%, {count} разів)\n"
                
                if top_triangular:
                    message += "\n<b>Найкращі трикутні шляхи:</b>\n"
                    for i, stats in enumerate(top_triangular, 1):
                        exchange = stats.get('exchange', '')
                        path = stats.get('path', [])
                        path_str = ' → '.join(path) if path else 'невідомо'
                        avg_net = stats.get('avg_net_profit', 0)
                        count = stats.get('count', 0)
                        
                        message += f"{i}. <b>{exchange}:</b> {path_str} "
                        message += f"(срд. {avg_net:.2f}%, {count} разів)\n"
            else:
                message += "Поки що немає даних для статистики."
            
            await self.send_message(message, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Помилка при обробці команди stats: {e}")
            await self.send_message(f"❌ Помилка при отриманні статистики: {e}", parse_mode="HTML")
    
    async def handle_top_command(self):
        """
        Обробляє команду /top
        """
        try:
            # Завантажуємо статус з файлу, якщо він є
            if os.path.exists("status.json"):
                with open("status.json", "r") as f:
                    status_info = json.load(f)
                
                # Показуємо топ можливості
                top_opps = status_info.get('top_opportunities', [])
                
                if top_opps:
                    message = "<b>🏆 Топ арбітражних можливостей</b>\n\n"
                    
                    for i, opp in enumerate(top_opps, 1):
                        symbol = opp.get('symbol', 'невідомо')
                        profit = opp.get('net_profit_percent', 0)
                        buy_ex = opp.get('buy_exchange', '')
                        sell_ex = opp.get('sell_exchange', '')
                        
                        # Визначаємо емодзі залежно від прибутку
                        profit_emoji = "🔥" if profit > 1.5 else "💰" if profit > 0.8 else "💸"
                        
                        if opp.get('opportunity_type') == 'triangular':
                            path = opp.get('path', [])
                            path_str = ' → '.join(path) if path else 'невідомо'
                            message += f"{i}. {profit_emoji} <b>{buy_ex}:</b> {path_str} ({profit:.2f}%)\n"
                        else:
                            message += f"{i}. {profit_emoji} <b>{symbol}:</b> {buy_ex} → {sell_ex} ({profit:.2f}%)\n"
                else:
                    message = "⚠️ На даний момент не знайдено арбітражних можливостей."
                
                await self.send_message(message, parse_mode="HTML")
            else:
                await self.send_message("⚠️ Немає доступної інформації про арбітражні можливості.", parse_mode="HTML")
                
        except Exception as e:
            logger.error(f"Помилка при обробці команди top: {e}")
            await self.send_message(f"❌ Помилка при отриманні топ можливостей: {e}", parse_mode="HTML")
