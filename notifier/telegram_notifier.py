# notifier/telegram_notifier.py
import logging
import asyncio
from typing import Any, Dict, Optional
import aiohttp

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
        
    async def initialize(self):
        """
        Ініціалізація HTTP-сесії
        """
        self.session = aiohttp.ClientSession()
        
    async def close(self):
        """
        Закриття HTTP-сесії
        """
        if self.session:
            await self.session.close()
            self.session = None
            
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
                
                # Відправляємо повідомлення
                success = await self._send_telegram_message(
                    message_data["message"], 
                    message_data.get("parse_mode")
                )
                
                if success:
                    logger.info("Повідомлення успішно відправлено")
                else:
                    logger.error("Не вдалося відправити повідомлення")
                    
                # Позначаємо задачу як виконану
                self.queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Обробник черги Telegram зупинено")
                break
            except Exception as e:
                logger.error(f"Помилка при обробці черги Telegram: {e}")
                
                # Позначаємо задачу як виконану, навіть якщо сталася помилка
                self.queue.task_done()
                
                # Невелика затримка перед наступною спробою
                await asyncio.sleep(1)
    
    async def _send_telegram_message(self, message: str, parse_mode: Optional[str] = None) -> bool:
        """
        Безпосередньо відправляє повідомлення в Telegram
        """
        if not self.session:
            await self.initialize()
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        params: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": message
        }
        
        if parse_mode:
            params["parse_mode"] = parse_mode
            
        try:
            async with self.session.post(url, json=params) as response:
                if response.status == 200:
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Помилка при відправці повідомлення: {response.status} - {response_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Виняток при відправці повідомлення: {e}")
            return False
