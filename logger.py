# logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
import config

# Створюємо директорію для логів, якщо вона не існує
os.makedirs(os.path.dirname(config.MAIN_LOG_FILE), exist_ok=True)

# Загальний формат логування з назвою програми та версією
log_format = logging.Formatter(f'%(asctime)s - {config.APP_NAME} v{config.VERSION} - %(name)s - %(levelname)s - %(message)s')

# Налаштування основного логера
main_logger = logging.getLogger('main')
main_logger.setLevel(getattr(logging, config.LOG_LEVEL))
main_handler = RotatingFileHandler(
    config.MAIN_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
main_handler.setFormatter(log_format)
main_logger.addHandler(main_handler)

# Налаштування логера для Telegram
telegram_logger = logging.getLogger('telegram')
telegram_logger.setLevel(getattr(logging, config.LOG_LEVEL))
telegram_handler = RotatingFileHandler(
    config.TELEGRAM_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
telegram_handler.setFormatter(log_format)
telegram_logger.addHandler(telegram_handler)

# Налаштування логера для арбітражу
arbitrage_logger = logging.getLogger('arbitrage')
arbitrage_logger.setLevel(getattr(logging, config.LOG_LEVEL))
arbitrage_handler = RotatingFileHandler(
    config.ARBITRAGE_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
arbitrage_handler.setFormatter(log_format)
arbitrage_logger.addHandler(arbitrage_handler)

# Налаштування логера для трикутного арбітражу
triangular_logger = logging.getLogger('triangular')
triangular_logger.setLevel(getattr(logging, config.LOG_LEVEL))
triangular_handler = RotatingFileHandler(
    config.TRIANGULAR_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
triangular_handler.setFormatter(log_format)
triangular_logger.addHandler(triangular_handler)

# Налаштування логера для бірж
exchanges_logger = logging.getLogger('exchanges')
exchanges_logger.setLevel(getattr(logging, config.LOG_LEVEL))
exchanges_handler = RotatingFileHandler(
    config.EXCHANGES_LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
exchanges_handler.setFormatter(log_format)
exchanges_logger.addHandler(exchanges_handler)

# Налаштування детального логера
debug_logger = logging.getLogger('debug')
debug_logger.setLevel(logging.DEBUG)  # Завжди зберігаємо максимальний рівень деталізації
debug_handler = RotatingFileHandler(
    config.DEBUG_LOG_FILE, 
    maxBytes=20*1024*1024,  # 20MB для більшого обсягу даних
    backupCount=5
)
debug_handler.setFormatter(log_format)
debug_logger.addHandler(debug_handler)

# Додамо також вивід в консоль для всіх логерів
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
console_handler.setLevel(getattr(logging, config.LOG_LEVEL))

main_logger.addHandler(console_handler)
telegram_logger.addHandler(console_handler)
arbitrage_logger.addHandler(console_handler)
triangular_logger.addHandler(console_handler)
exchanges_logger.addHandler(console_handler)
# Не додаємо debug_logger до консолі, щоб не перевантажувати її

# Глобальна функція для отримання логера
def get_logger(name):
    return logging.getLogger(name)
