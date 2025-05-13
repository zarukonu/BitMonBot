# logger.py
import logging
import os
from logging.handlers import RotatingFileHandler

# Створюємо директорію для логів, якщо вона не існує
logs_dir = 'logs'
os.makedirs(logs_dir, exist_ok=True)

# Шляхи до лог-файлів
MAIN_LOG_FILE = os.path.join(logs_dir, 'main.log')
TELEGRAM_LOG_FILE = os.path.join(logs_dir, 'telegram.log')
ARBITRAGE_LOG_FILE = os.path.join(logs_dir, 'arbitrage.log')
USERS_LOG_FILE = os.path.join(logs_dir, 'users.log')
TRIANGULAR_LOG_FILE = os.path.join(logs_dir, 'triangular.log')  # Лог для трикутного арбітражу
ALL_OPPORTUNITIES_LOG_FILE = os.path.join(logs_dir, 'all_opportunities.log')  # Новий лог для всіх можливостей

# Загальний формат логування
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Налаштування основного логера
main_logger = logging.getLogger('main')
main_logger.setLevel(logging.INFO)
main_handler = RotatingFileHandler(
    MAIN_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
main_handler.setFormatter(log_format)
main_logger.addHandler(main_handler)

# Налаштування логера для Telegram
telegram_logger = logging.getLogger('telegram')
telegram_logger.setLevel(logging.INFO)
telegram_handler = RotatingFileHandler(
    TELEGRAM_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
telegram_handler.setFormatter(log_format)
telegram_logger.addHandler(telegram_handler)

# Налаштування логера для арбітражу
arbitrage_logger = logging.getLogger('arbitrage')
arbitrage_logger.setLevel(logging.INFO)
arbitrage_handler = RotatingFileHandler(
    ARBITRAGE_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
arbitrage_handler.setFormatter(log_format)
arbitrage_logger.addHandler(arbitrage_handler)

# Налаштування логера для користувачів
users_logger = logging.getLogger('users')
users_logger.setLevel(logging.INFO)
users_handler = RotatingFileHandler(
    USERS_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
users_handler.setFormatter(log_format)
users_logger.addHandler(users_handler)

# Налаштування логера для трикутного арбітражу
triangular_logger = logging.getLogger('triangular')
triangular_logger.setLevel(logging.INFO)
triangular_handler = RotatingFileHandler(
    TRIANGULAR_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
triangular_handler.setFormatter(log_format)
triangular_logger.addHandler(triangular_handler)

# Новий логер для всіх арбітражних можливостей
all_opportunities_logger = logging.getLogger('all_opportunities')
all_opportunities_logger.setLevel(logging.INFO)
all_opportunities_handler = RotatingFileHandler(
    ALL_OPPORTUNITIES_LOG_FILE, 
    maxBytes=20*1024*1024,  # 20MB
    backupCount=10
)
all_opportunities_handler.setFormatter(log_format)
all_opportunities_logger.addHandler(all_opportunities_handler)

# Додамо також вивід в консоль для всіх логерів
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)

main_logger.addHandler(console_handler)
telegram_logger.addHandler(console_handler)
arbitrage_logger.addHandler(console_handler)
users_logger.addHandler(console_handler)
triangular_logger.addHandler(console_handler)
# Не додаємо консольний хендлер для all_opportunities, щоб не засмічувати консоль
