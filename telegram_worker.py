# telegram_worker.py
import asyncio
import logging
from typing import Optional, Dict, Any
import time
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
        self.monitoring_task: Optional[asyncio.Task] = None
        self.start_time = time.time()
        self.messages_sent = 0
        self.messages_failed = 0
        
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
        
        # Запускаємо моніторинг черги
        self.monitoring_task = asyncio.create_task(self._monitor_queue())
        
        # Відправляємо повідомлення про старт бота
        await self.notifier.send_formatted_message(config.START_MESSAGE)
        
        logger.info("Telegram Worker успішно запущено")
        
    async def stop(self):
        """
        Зупиняє воркер
        """
        logger.info("Зупинка Telegram Worker...")
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
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
        
    async def send_message(self, message: str, parse_mode: Optional[str] = None) -> bool:
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
            
    async def get_queue_info(self) -> Dict[str, Any]:
        """
        Повертає інформацію про стан черги повідомлень
        """
        if not self.queue:
            return {
                "status": "not_initialized",
                "queue_size": 0,
                "uptime_seconds": 0,
                "messages_sent": 0,
                "messages_failed": 0
            }
            
        return {
            "status": "running",
            "queue_size": self.queue.qsize(),
            "uptime_seconds": int(time.time() - self.start_time),
            "messages_sent": self.messages_sent,
            "messages_failed": self.messages_failed
        }
        
    async def send_queue_status(self):
        """
        Відправляє інформацію про стан черги в Telegram
        """
        if not self.notifier:
            logger.error("Неможливо відправити статус черги - Telegram Worker не запущено")
            return False
            
        queue_info = await self.get_queue_info()
        uptime_hours = queue_info["uptime_seconds"] // 3600
        uptime_minutes = (queue_info["uptime_seconds"] % 3600) // 60
        uptime_seconds = queue_info["uptime_seconds"] % 60
        
        status_message = (
            f"<b>📊 Статус Telegram сервісу</b>\n\n"
            f"<b>Стан:</b> {'Працює' if queue_info['status'] == 'running' else 'Не ініціалізовано'}\n"
            f"<b>Розмір черги:</b> {queue_info['queue_size']} повідомлень\n"
            f"<b>Час роботи:</b> {uptime_hours:02d}:{uptime_minutes:02d}:{uptime_seconds:02d}\n"
            f"<b>Відправлено повідомлень:</b> {queue_info['messages_sent']}\n"
            f"<b>Невдалих відправок:</b> {queue_info['messages_failed']}"
        )
        
        return await self.notifier.send_formatted_message(status_message, parse_mode="HTML")
        
    async def _monitor_queue(self):
        """
        Періодично моніторить стан черги та логує її статус
        """
        try:
            while True:
                queue_info = await self.get_queue_info()
                logger.info(f"Статус черги: {queue_info['queue_size']} повідомлень в черзі, "
                           f"{queue_info['messages_sent']} відправлено, "
                           f"{queue_info['messages_failed']} невдалих")
                
                # Відправляємо статус у Telegram тільки якщо є повідомлення в черзі
                # або минув певний час з моменту останньої перевірки
                if queue_info['queue_size'] > 5:
                    await self.send_queue_status()
                    
                await asyncio.sleep(config.QUEUE_STATUS_INTERVAL)
        except asyncio.CancelledError:
            logger.info("Моніторинг черги зупинено")
        except Exception as e:
            logger.error(f"Помилка при моніторингу черги: {e}")
