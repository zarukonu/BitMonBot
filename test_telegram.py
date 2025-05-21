#!/usr/bin/env python3
# test_telegram.py
import asyncio
import aiohttp
import sys
import os
import json
from datetime import datetime
import logging

# Налаштовуємо шлях до проєкту
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Налаштовуємо логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_telegram')

# Імпортуємо конфігурацію
try:
    import config
    TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID
except ImportError as e:
    logger.error(f"Помилка імпорту конфігурації: {e}")
    sys.exit(1)

async def test_telegram_api():
    """
    Перевіряє з'єднання з Telegram API
    """
    logger.info("Перевірка з'єднання з Telegram API...")
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        bot_info = data["result"]
                        logger.info(f"З'єднання з Telegram API успішне!")
                        logger.info(f"Інформація про бота:")
                        logger.info(f"ID: {bot_info.get('id')}")
                        logger.info(f"Логін: @{bot_info.get('username')}")
                        logger.info(f"Ім'я: {bot_info.get('first_name')}")
                        return True
                    else:
                        logger.error(f"Помилка API Telegram: {data.get('description', 'Невідома помилка')}")
                else:
                    logger.error(f"Помилка з'єднання з Telegram API: {response.status} - {await response.text()}")
    except Exception as e:
        logger.error(f"Помилка при перевірці з'єднання з Telegram API: {e}")
    
    return False

async def send_test_message():
    """
    Надсилає тестове повідомлення через Telegram API
    """
    logger.info("Надсилання тестового повідомлення...")
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": f"🧪 <b>Тестове повідомлення</b>\n\nЦе тестове повідомлення для перевірки роботи Telegram API.\nЧас: {timestamp}",
                "parse_mode": "HTML"
            }
            
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    logger.info("Тестове повідомлення успішно надіслано!")
                    return True
                else:
                    logger.error(f"Помилка при надсиланні повідомлення: {response.status} - {await response.text()}")
    except Exception as e:
        logger.error(f"Помилка при надсиланні тестового повідомлення: {e}")
    
    return False

async def check_updates():
    """
    Перевіряє наявність оновлень від користувачів
    """
    logger.info("Перевірка наявності оновлень від користувачів...")
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?limit=5"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        updates = data.get("result", [])
                        logger.info(f"Отримано {len(updates)} оновлень")
                        
                        if updates:
                            for update in updates:
                                update_id = update.get("update_id")
                                message = update.get("message")
                                
                                if message:
                                    chat_id = message.get("chat", {}).get("id")
                                    text = message.get("text", "")
                                    from_user = message.get("from", {})
                                    username = from_user.get("username", "")
                                    first_name = from_user.get("first_name", "")
                                    
                                    logger.info(f"Повідомлення #{update_id} від {first_name} (@{username}): {text}")
                        else:
                            logger.info("Немає нових повідомлень")
                        
                        return True
                    else:
                        logger.error(f"Помилка API Telegram: {data.get('description', 'Невідома помилка')}")
                else:
                    logger.error(f"Помилка при отриманні оновлень: {response.status} - {await response.text()}")
    except Exception as e:
        logger.error(f"Помилка при перевірці оновлень: {e}")
    
    return False

async def main():
    """
    Основна функція
    """
    # Перевіряємо з'єднання з Telegram API
    api_ok = await test_telegram_api()
    
    if not api_ok:
        logger.error("Помилка з'єднання з Telegram API. Перевірте токен бота.")
        return
    
    # Надсилаємо тестове повідомлення
    send_ok = await send_test_message()
    
    if not send_ok:
        logger.error("Не вдалося надіслати тестове повідомлення. Перевірте ID чату та права бота.")
        return
    
    # Перевіряємо оновлення
    updates_ok = await check_updates()
    
    if not updates_ok:
        logger.error("Не вдалося отримати оновлення від Telegram API.")
        return
    
    logger.info("Тестування Telegram компонента успішно завершено!")

if __name__ == "__main__":
    asyncio.run(main())
