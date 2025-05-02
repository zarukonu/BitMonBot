# telegram_worker.py
import asyncio
import logging
import time
from typing import Optional
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
        self.monitor_task: Optional[asyncio.Task] = None
        
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
        self.monitor_task = asyncio.create_task(self.monitor_queue())
        
        # Відправляємо повідомлення про старт бота
        await self.notifier.send_formatted_message(config.START_MESSAGE)
        
        logger.info("Telegram Worker успішно запущено")
        
    async def stop(self):
        """
        Зупиняє воркер
        """
        logger.info("Зупинка Telegram Worker...")
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        # Чекаємо завершення відправки всіх повідомлень
        if self.queue and not self.queue.empty():
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
