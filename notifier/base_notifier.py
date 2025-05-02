# notifier/base_notifier.py
from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseNotifier(ABC):
    """
    Абстрактний базовий клас для систем сповіщень
    """
    @abstractmethod
    async def send_message(self, message: str, chat_id: Optional[str] = None) -> bool:
        """
        Надсилає повідомлення
        
        Args:
            message (str): Текст повідомлення
            chat_id (Optional[str]): Ідентифікатор чату (опціонально)
            
        Returns:
            bool: True у разі успіху, False у разі невдачі
        """
        pass
    
    @abstractmethod
    async def send_formatted_message(self, message: str, chat_id: Optional[str] = None, parse_mode: Optional[str] = None) -> bool:
        """
        Надсилає форматоване повідомлення
        
        Args:
            message (str): Текст повідомлення
            chat_id (Optional[str]): Ідентифікатор чату (опціонально)
            parse_mode (Optional[str]): Режим форматування
            
        Returns:
            bool: True у разі успіху, False у разі невдачі
        """
        pass
