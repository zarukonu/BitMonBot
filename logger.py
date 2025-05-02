# logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
import config

# Створюємо директорію для логів, якщо вона не існує
os.makedirs(os.path.dirname(config.MAIN_LOG_FILE), exist_ok=True)

# Загальний формат логування з назвою програми
log_format = logging.Formatter(f'%(asctime)s - {config.APP_NAME} - %(name)s - %(levelname)s - %(message)s')

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

# Додамо також вивід в консоль для всіх логерів
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)

# Перевіряємо, чи логери вже мають обробники
if not main_logger.handlers:
    main_logger.addHandler(main_handler)
    main_logger.addHandler(console_handler)
else:
    # Якщо обробники вже існують, переконаємося, що консольний обробник присутній
    has_console_handler = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) 
                            for h in main_logger.handlers)
    if not has_console_handler:
        main_logger.addHandler(console_handler)

if not telegram_logger.handlers:
    telegram_logger.addHandler(telegram_handler)
    telegram_logger.addHandler(console_handler)
else:
    has_console_handler = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) 
                            for h in telegram_logger.handlers)
    if not has_console_handler:
        telegram_logger.addHandler(console_handler)

if not arbitrage_logger.handlers:
    arbitrage_logger.addHandler(arbitrage_handler)
    arbitrage_logger.addHandler(console_handler)
else:
    has_console_handler = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) 
                            for h in arbitrage_logger.handlers)
    if not has_console_handler:
        arbitrage_logger.addHandler(console_handler)

# Створення директорії для логів
os.makedirs(os.path.dirname(config.MAIN_LOG_FILE), exist_ok=True)
