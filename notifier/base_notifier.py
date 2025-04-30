# notifier/base_notifier.py
from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseNotifier(ABC):
    """
    Абстрактний базовий клас для систем сповіщень
    """
    @abstractmethod
    async def send_message(self, message: str) -> bool:
        """
        Надсилає повідомлення
        
        Args:
            message (str): Текст повідомлення
            
        Returns:
            bool: True у разі успіху, False у разі невдачі
        """
        pass
    
    @abstractmethod
    async def send_formatted_message(self, message: str, parse_mode: Optional[str] = None) -> bool:
        """
        Надсилає форматоване повідомлення
        
        Args:
            message (str): Текст повідомлення
            parse_mode (Optional[str]): Режим форматування
            
        Returns:
            bool: True у разі успіху, False у разі невдачі
        """
        pass
