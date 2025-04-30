# notifier/telegram_notifier.py
import logging
import asyncio
from typing import Any, Dict, Optional
import aiohttp
import time

from notifier.base_notifier import BaseNotifier
import config

logger = logging.getLogger('telegram')

class TelegramNotifier(BaseNotifier):
    """
    Клас для надсилання повідомлень у Telegram
    """
    def __init__(self, bot_token: str, chat_id: str, queue: asyncio.Queue):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.queue = queue
        self.session: Optional[aiohttp.ClientSession] = None
        self.messages_sent = 0
        self.messages_failed = 0
        self.last_rate_limit_time = 0
        
    async def initialize(self):
        """
        Ініціалізація HTTP-сесії
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            logger.info("Ініціалізовано HTTP-сесію для Telegram")
        
    async def close(self):
        """
        Закриття HTTP-сесії
        """
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            logger.info("Закрито HTTP-сесію Telegram")
            
    async def send_message(self, message: str) -> bool:
        """
        Ставить повідомлення в чергу на відправку
        """
        await self.queue.put({"message": message, "parse_mode": None})
        logger.debug(f"Повідомлення додано в чергу. Поточна довжина черги: {self.queue.qsize()}")
        return True
        
    async def send_formatted_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Ставить форматоване повідомлення в чергу на відправку
        """
        await self.queue.put({"message": message, "parse_mode": parse_mode})
        logger.debug(f"Форматоване повідомлення додано в чергу. Поточна довжина черги: {self.queue.qsize()}")
        return True
        
    async def process_queue(self):
        """
        Обробляє чергу повідомлень
        """
        if not self.session:
            await self.initialize()
            
        while True:
            try:
                # Отримуємо повідомлення з черги
                message_data = await self.queue.get()
                
                # Перевіряємо обмеження швидкості (не більше 30 повідомлень на хвилину)
                current_time = time.time()
                if current_time - self.last_rate_limit_time < 2:
                    await asyncio.sleep(2)
                
                # Відправляємо повідомлення
                start_time = time.time()
                success = await self._send_telegram_message(
                    message_data["message"], 
                    message_data.get("parse_mode")
                )
                
                self.last_rate_limit_time = time.time()
                
                if success:
                    self.messages_sent += 1
                    logger.info(f"Повідомлення успішно відправлено (за {(time.time() - start_time):.2f} сек)")
                else:
                    self.messages_failed += 1
                    logger.error(f"Не вдалося відправити повідомлення (за {(time.time() - start_time):.2f} сек)")
                    
                # Позначаємо задачу як виконану
                self.queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Обробник черги Telegram зупинено")
                break
            except Exception as e:
                logger.error(f"Помилка при обробці черги Telegram: {e}")
                self.messages_failed += 1
                
                # Позначаємо задачу як виконану, навіть якщо сталася помилка
                self.queue.task_done()
                
                # Невелика затримка перед наступною спробою
                await asyncio.sleep(1)
    
    async def _send_telegram_message(self, message: str, parse_mode: Optional[str] = None) -> bool:
        """
        Безпосередньо відправляє повідомлення в Telegram
        """
        if not self.session or self.session.closed:
            await self.initialize()
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        params: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": message
        }
        
        if parse_mode:
            params["parse_mode"] = parse_mode
            
        try:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    async with self.session.post(url, json=params, timeout=10) as response:
                        if response.status == 200:
                            return True
                        # Якщо отримали помилку 429 (Too Many Requests), чекаємо і пробуємо знову
                        elif response.status == 429:
                            retry_count += 1
                            wait_time = 5 * retry_count
                            logger.warning(f"Перевищено ліміт запитів до Telegram API. Чекаємо {wait_time} секунд...")
                            await asyncio.sleep(wait_time)
                        else:
                            response_text = await response.text()
                            logger.error(f"Помилка при відправці повідомлення: {response.status} - {response_text}")
                            return False
                except asyncio.TimeoutError:
                    retry_count += 1
                    logger.warning(f"Таймаут при відправці повідомлення. Спроба {retry_count}/{max_retries}")
                    await asyncio.sleep(2)
                    
            # Якщо дійшли сюди, значить всі спроби невдалі
            return False
                    
        except Exception as e:
            logger.error(f"Виняток при відправці повідомлення: {e}")
            return False
