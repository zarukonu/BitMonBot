#!/usr/bin/env python3
# telegram_watchdog.py
import asyncio
import logging
import os
import sys
import json
import time
from datetime import datetime, timedelta
import subprocess
import traceback
import signal
import aiohttp

# Налаштовуємо шлях до проєкту
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Налаштовуємо логування
log_dir = os.path.join(script_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "telegram_watchdog.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('telegram_watchdog')

# Імпортуємо конфігурацію
try:
    import config
    TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID
    ADMIN_USER_IDS = config.ADMIN_USER_IDS
except ImportError as e:
    logger.error(f"Помилка імпорту конфігурації: {e}")
    sys.exit(1)

# Шляхи до файлів
MAIN_SCRIPT = os.path.join(script_dir, "main.py")
STATUS_FILE = os.path.join(script_dir, "status.json")
TELEGRAM_STATUS_FILE = os.path.join(script_dir, "status", "telegram_status.json")
TELEGRAM_LOG_FILE = os.path.join(log_dir, "telegram.log")

# Константи для моніторингу
CHECK_INTERVAL = 300  # 5 хвилин
MAX_TIME_WITHOUT_UPDATES = 600  # 10 хвилин
MAX_RETRIES = 3  # Максимальна кількість спроб перезапуску

class TelegramWatchdog:
    def __init__(self):
        self.telegram_bot_token = TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = TELEGRAM_CHAT_ID
        self.admin_user_ids = ADMIN_USER_IDS
        self.session = None
        self.retry_count = 0
    
    async def initialize(self):
        """
        Ініціалізує HTTP сесію
        """
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """
        Закриває HTTP сесію
        """
        if self.session:
            await self.session.close()
    
    async def check_telegram_api(self):
        """
        Перевіряє з'єднання з Telegram API
        """
        if not self.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не встановлено")
            return False
        
        try:
            if not self.session:
                await self.initialize()
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getMe"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        logger.info(f"З'єднання з Telegram API успішне. Бот: {data['result'].get('username')}")
                        return True
                    else:
                        logger.error(f"Помилка API Telegram: {data.get('description', 'Невідома помилка')}")
                else:
                    logger.error(f"Помилка з'єднання з Telegram API: {response.status}")
        except Exception as e:
            logger.error(f"Помилка при перевірці з'єднання з Telegram API: {e}")
        
        return False
    
    async def send_telegram_message(self, message, chat_id=None):
        """
        Надсилає повідомлення через Telegram API
        """
        if not self.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не встановлено")
            return False
        
        if chat_id is None:
            chat_id = self.telegram_chat_id
        
        try:
            if not self.session:
                await self.initialize()
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.info(f"Повідомлення успішно надіслано в чат {chat_id}")
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Помилка при надсиланні повідомлення: {response.status} - {response_text}")
        except Exception as e:
            logger.error(f"Помилка при надсиланні повідомлення: {e}")
        
        return False
    
    async def notify_admins(self, message):
        """
        Надсилає повідомлення всім адміністраторам
        """
        for admin_id in self.admin_user_ids:
            try:
                await self.send_telegram_message(message, admin_id)
            except Exception as e:
                logger.error(f"Помилка при сповіщенні адміністратора {admin_id}: {e}")
    
    def check_bot_process(self):
        """
        Перевіряє, чи працює процес бота
        """
        try:
            result = subprocess.run(["pgrep", "-f", "main.py"], capture_output=True, text=True)
            pids = result.stdout.strip().split('\n')
            
            if pids and pids[0]:
                logger.info(f"Знайдено процеси бота: {pids}")
                return True
            else:
                logger.warning("Не знайдено процесів бота")
                return False
        except Exception as e:
            logger.error(f"Помилка при перевірці процесів бота: {e}")
            return False
    
    def check_telegram_logs(self):
        """
        Перевіряє логи Telegram на наявність свіжих записів
        """
        if not os.path.exists(TELEGRAM_LOG_FILE):
            logger.error(f"Файл логів {TELEGRAM_LOG_FILE} не знайдено")
            return False
        
        try:
            # Отримуємо час останньої модифікації файлу
            mtime = os.path.getmtime(TELEGRAM_LOG_FILE)
            mtime_dt = datetime.fromtimestamp(mtime)
            
            # Перевіряємо, чи оновлювався файл логів останні 10 хвилин
            time_diff = datetime.now() - mtime_dt
            logger.info(f"Час останньої модифікації логів Telegram: {mtime_dt}, різниця: {time_diff}")
            
            if time_diff > timedelta(minutes=10):
                logger.warning(f"Файл логів Telegram не оновлювався останні 10 хвилин")
                return False
            
            # Перевіряємо останні рядки логу
            with open(TELEGRAM_LOG_FILE, 'r') as f:
                # Отримуємо останні 100 рядків
                lines = f.readlines()[-100:]
                
                # Шукаємо в логах записи про успішну відправку повідомлень
                found_recent_activity = False
                for line in reversed(lines):
                    # Перевіряємо, чи містить рядок дату і час
                    if " - telegram - " not in line:
                        continue
                    
                    # Отримуємо дату і час з рядка
                    try:
                        line_parts = line.split(' - ', 2)
                        if len(line_parts) < 2:
                            continue
                        
                        log_datetime_str = line_parts[0]
                        log_datetime = datetime.strptime(log_datetime_str, "%Y-%m-%d %H:%M:%S,%f")
                        
                        # Перевіряємо, чи лог не старіший за 10 хвилин
                        if datetime.now() - log_datetime < timedelta(minutes=10):
                            logger.info(f"Знайдено активність в логах Telegram за останні 10 хвилин")
                            found_recent_activity = True
                            break
                    except Exception as e:
                        continue
                
                if not found_recent_activity:
                    logger.warning("Не знайдено активності в логах Telegram за останні 10 хвилин")
                
                return found_recent_activity
        except Exception as e:
            logger.error(f"Помилка при перевірці логів Telegram: {e}")
        
        return False
    
    def check_telegram_status_file(self):
        """
        Перевіряє файл статусу Telegram
        """
        try:
            if os.path.exists(TELEGRAM_STATUS_FILE):
                with open(TELEGRAM_STATUS_FILE, 'r') as f:
                    status = json.load(f)
                
                last_check = status.get('last_check')
                if last_check:
                    last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                    time_diff = datetime.now() - last_check_dt
                    
                    logger.info(f"Час останньої перевірки статусу Telegram: {last_check_dt}, різниця: {time_diff}")
                    
                    if time_diff > timedelta(minutes=10):
                        logger.warning("Статус Telegram не оновлювався останні 10 хвилин")
                        return False
                    
                    return True
                else:
                    logger.warning("У файлі статусу відсутня інформація про останню перевірку")
            else:
                logger.warning(f"Файл статусу {TELEGRAM_STATUS_FILE} не знайдено")
        except Exception as e:
            logger.error(f"Помилка при перевірці файлу статусу Telegram: {e}")
        
        return False
    
    def restart_bot(self):
        """
        Перезапускає бота
        """
        try:
            # Шукаємо процеси бота
            result = subprocess.run(["pgrep", "-f", "main.py"], capture_output=True, text=True)
            pids = result.stdout.strip().split('\n')
            
            # Зупиняємо всі процеси бота
            if pids and pids[0]:
                for pid in pids:
                    if not pid:
                        continue
                    
                    logger.info(f"Зупинка процесу бота з PID {pid}")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except Exception as e:
                        logger.error(f"Помилка при зупинці процесу {pid}: {e}")
                
                # Чекаємо на завершення процесів
                time.sleep(5)
                
                # Перевіряємо, чи всі процеси завершено
                result = subprocess.run(["pgrep", "-f", "main.py"], capture_output=True, text=True)
                pids = result.stdout.strip().split('\n')
                
                if pids and pids[0]:
                    logger.warning("Деякі процеси бота не завершилися. Спроба примусового завершення.")
                    for pid in pids:
                        if not pid:
                            continue
                        
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except Exception as e:
                            logger.error(f"Помилка при примусовому завершенні процесу {pid}: {e}")
                    
                    time.sleep(2)
            
          # Запускаємо бота
            logger.info(f"Запуск бота: python3 {MAIN_SCRIPT}")
            subprocess.Popen(
                ["python3", MAIN_SCRIPT],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=script_dir
            )
            
            # Очікуємо, щоб дати боту час на ініціалізацію
            time.sleep(30)
            
            # Перевіряємо, чи бот запустився
            result = subprocess.run(["pgrep", "-f", "main.py"], capture_output=True, text=True)
            pids = result.stdout.strip().split('\n')
            
            if pids and pids[0]:
                logger.info(f"Бот успішно запущено, PID: {pids}")
                self.retry_count = 0  # Скидаємо лічильник спроб
                return True
            else:
                logger.error("Не вдалося запустити бота")
                self.retry_count += 1
                return False
                
        except Exception as e:
            logger.error(f"Помилка при перезапуску бота: {e}")
            logger.error(traceback.format_exc())
            self.retry_count += 1
            return False
    
    async def run(self):
        """
        Основний цикл роботи watchdog
        """
        logger.info("Запуск Telegram Watchdog")
        
        try:
            # Ініціалізуємо HTTP сесію
            await self.initialize()
            
            # Перевіряємо з'єднання з Telegram API
            api_ok = await self.check_telegram_api()
            if not api_ok:
                logger.error("Не вдалося з'єднатися з Telegram API. Watchdog не може працювати.")
                return
            
            # Основний цикл моніторингу
            while True:
                try:
                    logger.info("Перевірка стану Telegram компонента...")
                    
                    # Перевіряємо, чи працює процес бота
                    process_ok = self.check_bot_process()
                    if not process_ok:
                        logger.warning("Процес бота не запущено")
                        await self.notify_admins(
                            "⚠️ <b>Виявлено проблему:</b> процес бота не запущено! Спроба перезапуску..."
                        )
                        if self.restart_bot():
                            await self.notify_admins("✅ Бот успішно перезапущено")
                        else:
                            await self.notify_admins(
                                f"❌ Не вдалося перезапустити бота (спроба {self.retry_count}/{MAX_RETRIES})"
                            )
                        
                        # Якщо перевищено максимальну кількість спроб, виходимо
                        if self.retry_count >= MAX_RETRIES:
                            logger.error(f"Перевищено максимальну кількість спроб ({MAX_RETRIES}). Виходимо.")
                            await self.notify_admins(
                                "❌ Перевищено максимальну кількість спроб перезапуску. Потрібне ручне втручання."
                            )
                            break
                        
                        # Переходимо до наступної ітерації
                        await asyncio.sleep(CHECK_INTERVAL)
                        continue
                    
                    # Перевіряємо логи Telegram
                    logs_ok = self.check_telegram_logs()
                    
                    # Перевіряємо файл статусу Telegram
                    status_ok = self.check_telegram_status_file()
                    
                    # Якщо хоч один з індикаторів активності в порядку, вважаємо, що все працює
                    telegram_ok = logs_ok or status_ok
                    
                    if not telegram_ok:
                        logger.warning("Telegram компонент може бути неактивним")
                        await self.notify_admins(
                            "⚠️ <b>Виявлено проблему з Telegram компонентом!</b>\n\n"
                            "Telegram Worker не показує ознак активності. Спроба перезапуску бота..."
                        )
                        
                        if self.restart_bot():
                            await self.notify_admins("✅ Бот успішно перезапущено")
                        else:
                            await self.notify_admins(
                                f"❌ Не вдалося перезапустити бота (спроба {self.retry_count}/{MAX_RETRIES})"
                            )
                        
                        # Якщо перевищено максимальну кількість спроб, виходимо
                        if self.retry_count >= MAX_RETRIES:
                            logger.error(f"Перевищено максимальну кількість спроб ({MAX_RETRIES}). Виходимо.")
                            await self.notify_admins(
                                "❌ Перевищено максимальну кількість спроб перезапуску. Потрібне ручне втручання."
                            )
                            break
                    else:
                        logger.info("Telegram компонент працює нормально")
                        # Скидаємо лічильник спроб
                        self.retry_count = 0
                    
                    # Чекаємо до наступної перевірки
                    await asyncio.sleep(CHECK_INTERVAL)
                    
                except asyncio.CancelledError:
                    logger.info("Telegram Watchdog зупинено")
                    break
                except Exception as e:
                    logger.error(f"Помилка в основному циклі Telegram Watchdog: {e}")
                    logger.error(traceback.format_exc())
                    await asyncio.sleep(60)  # Чекаємо 1 хвилину перед повторною спробою
        
        finally:
            # Закриваємо HTTP сесію
            await self.close()
            logger.info("Telegram Watchdog завершено")

async def main():
    """
    Точка входу для Telegram Watchdog
    """
    # Створюємо директорії для логів і статусів, якщо вони не існують
    os.makedirs(os.path.join(script_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "status"), exist_ok=True)
    
    # Запускаємо watchdog
    watchdog = TelegramWatchdog()
    await watchdog.run()

if __name__ == "__main__":
    # Запускаємо асинхронний цикл
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Програму зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}")
        logger.error(traceback.format_exc())
