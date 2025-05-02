# notifier/telegram_notifier.py
import logging
import asyncio
import time
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
        self.last_sent_time = 0  # Час останньої відправки повідомлення
        self.rate_limit = 0.5  # Мінімальний інтервал між повідомленнями в секундах
        self.retry_count = 3  # Кількість повторних спроб
        self.retry_delay = 2  # Затримка між повторними спробами в секундах
        self.messages_sent = 0  # Лічильник відправлених повідомлень
        self.messages_failed = 0  # Лічильник невдалих відправок
        
    async def initialize(self):
        """
        Ініціалізація HTTP-сесії
        """
        self.session = aiohttp.ClientSession()
        logger.info("HTTP-сесію ініціалізовано")
        
    async def close(self):
        """
        Закриття HTTP-сесії
        """
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("HTTP-сесію закрито")
            
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
            
        logger.info("Обробник черги Telegram запущено")
        
        while True:
            try:
                # Отримуємо повідомлення з черги
                message_data = await self.queue.get()
                
                # Обмеження швидкості відправки повідомлень
                current_time = time.time()
                time_since_last = current_time - self.last_sent_time
                
                if time_since_last < self.rate_limit:
                    delay = self.rate_limit - time_since_last
                    logger.debug(f"Обмеження швидкості: очікування {delay:.2f} секунд")
                    await asyncio.sleep(delay)
                
                # Відправляємо повідомлення з повторними спробами
                start_time = time.time()
                success = False
                
                for attempt in range(self.retry_count):
                    try:
                        success = await self._send_telegram_message(
                            message_data["message"], 
                            message_data.get("parse_mode")
                        )
                        
                        if success:
                            self.messages_sent += 1
                            self.last_sent_time = time.time()
                            send_time = time.time() - start_time
                            logger.info(f"Повідомлення успішно відправлено (спроба {attempt+1}, час: {send_time:.2f}с)")
                            break
                        else:
                            logger.warning(f"Не вдалося відправити повідомлення (спроба {attempt+1})")
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                    except Exception as e:
                        logger.error(f"Помилка при відправці повідомлення (спроба {attempt+1}): {e}")
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                
                if not success:
                    self.messages_failed += 1
                    logger.error(f"Всі спроби відправити повідомлення вичерпано. Повідомлення не відправлено.")
                    
                # Позначаємо задачу як виконану
                self.queue.task_done()
                
                # Логуємо статистику
                if (self.messages_sent + self.messages_failed) % 10 == 0:
                    logger.info(f"Статистика відправки: успішно - {self.messages_sent}, невдало - {self.messages_failed}")
                
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
            start_time = time.time()
            
            async with self.session.post(url, json=params) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    logger.debug(f"Telegram API відповів за {response_time:.3f} секунд")
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Помилка при відправці повідомлення: {response.status} - {response_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Виняток при відправці повідомлення: {e}")
            return False
