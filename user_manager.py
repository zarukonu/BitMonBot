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
    Клас для керування користувачами та їх доступом
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
            
            # Визначаємо тип користувача (адмін чи звичайний)
            is_admin = user_id in config.ADMIN_USER_IDS
            
            if is_new:
                # Створюємо нового користувача
                self.users[user_id] = {
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_admin": is_admin,
                    "is_approved": is_admin,  # Адміни автоматично схвалені
                    "active": True,
                    "created_at": datetime.datetime.now().isoformat(),
                    "last_activity": datetime.datetime.now().isoformat(),
                    "pairs": config.ALL_PAIRS[:],
                    "min_profit": config.DEFAULT_MIN_PROFIT,
                    "notifications_count": 0
                }
                users_logger.info(f"Додано нового користувача: {user_id} (admin: {is_admin})")
            else:
                # Оновлюємо існуючого користувача
                self.users[user_id]["username"] = username
                self.users[user_id]["first_name"] = first_name
                self.users[user_id]["last_name"] = last_name
                self.users[user_id]["last_activity"] = datetime.datetime.now().isoformat()
                
                # Якщо користувач став адміном, оновлюємо його статус
                if is_admin and not self.users[user_id].get("is_admin", False):
                    self.users[user_id]["is_admin"] = True
                    self.users[user_id]["is_approved"] = True
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
        
    def approve_user(self, user_id: str) -> bool:
        """
        Схвалює користувача
        """
        if user_id not in self.users:
            return False
            
        self.users[user_id]["is_approved"] = True
        self.update_user_activity(user_id)
        self.save_users()
        
        users_logger.info(f"Користувача {user_id} схвалено")
        return True
        
    def block_user(self, user_id: str) -> bool:
        """
        Блокує користувача
        """
        if user_id not in self.users:
            return False
            
        self.users[user_id]["is_approved"] = False
        self.update_user_activity(user_id)
        self.save_users()
        
        users_logger.info(f"Користувача {user_id} заблоковано")
        return True
        
    def update_user_pairs(self, user_id: str, pairs: List[str]) -> bool:
        """
        Оновлює список пар для користувача
        """
        if user_id not in self.users:
            return False
        
        # Перевіряємо, що всі пари підтримуються
        valid_pairs = [pair for pair in pairs if pair in config.ALL_PAIRS]
        
        if len(valid_pairs) != len(pairs)
