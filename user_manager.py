# user_manager.py
import logging
import json
from typing import Dict, List, Optional, Any
import datetime
import config

logger = logging.getLogger('main')
users_logger = logging.getLogger('users')

class UserManager:
    """
    Клас для керування користувачами та їх підписками
    """
    def __init__(self, users_file: str = config.USERS_FILE):
        self.users_file = users_file
        self.users = {}
        self.load_users()
        
    def load_users(self) -> bool:
        """
        Завантажує користувачів з файлу
        """
        try:
            self.users = config.load_users()
            users_logger.info(f"Завантажено {len(self.users)} користувачів")
            return True
        except Exception as e:
            users_logger.error(f"Помилка при завантаженні користувачів: {e}")
            return False
            
    def save_users(self) -> bool:
        """
        Зберігає користувачів у файл
        """
        try:
            result = config.save_users(self.users)
            if result:
                users_logger.info(f"Збережено {len(self.users)} користувачів")
            return result
        except Exception as e:
            users_logger.error(f"Помилка при збереженні користувачів: {e}")
            return False
            
    def add_user(self, user_id: str, username: str = "", first_name: str = "", 
                  last_name: str = "") -> bool:
        """
        Додає нового користувача або оновлює існуючого
        """
        try:
            is_new = user_id not in self.users
            
            # Визначаємо тип підписки (адмін чи звичайний)
            user_type = "admin" if user_id in config.ADMIN_USER_IDS else "free"
            
            if is_new:
                # Створюємо нового користувача
                self.users[user_id] = {
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "subscription_type": user_type,
                    "active": True,
                    "created_at": datetime.datetime.now().isoformat(),
                    "last_activity": datetime.datetime.now().isoformat(),
                    "pairs": config.PAIRS[:config.USER_SUBSCRIPTION_TYPES[user_type]["max_pairs"]],
                    "min_profit": config.DEFAULT_MIN_PROFIT,
                    "notifications_count": 0
                }
                users_logger.info(f"Додано нового користувача: {user_id} (тип: {user_type})")
            else:
                # Оновлюємо існуючого користувача
                self.users[user_id]["username"] = username
                self.users[user_id]["first_name"] = first_name
                self.users[user_id]["last_name"] = last_name
                self.users[user_id]["last_activity"] = datetime.datetime.now().isoformat()
                
                # Якщо користувач став адміном, оновлюємо його тип
                if user_type == "admin" and self.users[user_id]["subscription_type"] != "admin":
                    self.users[user_id]["subscription_type"] = "admin"
                    users_logger.info(f"Користувача {user_id} підвищено до адміністратора")
                
                users_logger.info(f"Оновлено дані користувача: {user_id}")
                
            self.save_users()
            return True
        except Exception as e:
            users_logger.error(f"Помилка при додаванні/оновленні користувача {user_id}: {e}")
            return False
            
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Отримує дані користувача
        """
        return self.users.get(user_id)
        
    def update_user_activity(self, user_id: str) -> bool:
        """
        Оновлює час останньої активності користувача
        """
        if user_id not in self.users:
            return False
            
        self.users[user_id]["last_activity"] = datetime.datetime.now().isoformat()
        return True
        
    def set_user_active(self, user_id: str, active: bool = True) -> bool:
        """
        Активує або деактивує користувача
        """
        if user_id not in self.users:
            return False
            
        self.users[user_id]["active"] = active
        self.update_user_activity(user_id)
        self.save_users()
        
        status = "активовано" if active else "деактивовано"
        users_logger.info(f"Користувача {user_id} {status}")
        return True
        
    def update_user_pairs(self, user_id: str, pairs: List[str]) -> bool:
        """
        Оновлює список пар для користувача
        """
        if user_id not in self.users:
            return False
            
        # Отримуємо максимальну кількість пар для підписки користувача
        subscription_type = self.users[user_id]["subscription_type"]
        max_pairs = config.USER_SUBSCRIPTION_TYPES[subscription_type]["max_pairs"]
        
        # Для безлімітних підписок (max_pairs = -1) обмеження немає
        if max_pairs != -1 and len(pairs) > max_pairs:
            users_logger.warning(
                f"Користувач {user_id} спробував встановити {len(pairs)} пар, "
                f"але його ліміт {max_pairs}. Список обрізано."
            )
            pairs = pairs[:max_pairs]
            
        # Перевіряємо, що всі пари підтримуються
        valid_pairs = [pair for pair in pairs if pair in config.PAIRS]
        
        if len(valid_pairs) != len(pairs):
            users_logger.warning(
                f"Користувач {user_id} спробував додати непідтримувані пари. "
                f"Додано лише підтримувані: {valid_pairs}"
            )
            
        self.users[user_id]["pairs"] = valid_pairs
        self.update_user_activity(user_id)
        self.save_users()
        
        users_logger.info(f"Оновлено пари для користувача {user_id}: {valid_pairs}")
        return True
        
    def set_user_min_profit(self, user_id: str, min_profit: float) -> bool:
        """
        Встановлює мінімальний поріг прибутку для користувача
        """
        if user_id not in self.users:
            return False
            
        # Обмежуємо значення в розумних межах
        if min_profit < 0.1:
            min_profit = 0.1
        elif min_profit > 10.0:
            min_profit = 10.0
            
        self.users[user_id]["min_profit"] = min_profit
        self.update_user_activity(user_id)
        self.save_users()
        
        users_logger.info(f"Встановлено мінімальний поріг прибутку для користувача {user_id}: {min_profit}%")
        return True
        
    def increment_notifications(self, user_id: str) -> int:
        """
        Збільшує лічильник відправлених повідомлень користувачу
        """
        if user_id not in self.users:
            return 0
            
        self.users[user_id]["notifications_count"] = self.users[user_id].get("notifications_count", 0) + 1
        self.save_users()
        
        return self.users[user_id]["notifications_count"]
        
    def get_active_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Повертає словник активних користувачів
        """
        return {user_id: user_data for user_id, user_data in self.users.items() 
                if user_data.get("active", False)}
                
    def get_user_notification_delay(self, user_id: str) -> int:
        """
        Повертає затримку для відправки повідомлень користувачу
        """
        if user_id not in self.users:
            return 0
            
        subscription_type = self.users[user_id]["subscription_type"]
        return config.USER_SUBSCRIPTION_TYPES[subscription_type]["notification_delay"]
