# update_thresholds.py
import json
import os
import config

def update_users_thresholds():
    """
    Оновлює мінімальний поріг прибутку для користувачів
    """
    print(f"Зміна порогів прибутку користувачів у файлі {config.USERS_FILE}")
    try:
        if os.path.exists(config.USERS_FILE):
            with open(config.USERS_FILE, 'r') as f:
                users = json.load(f)
            
            updated_count = 0
            for user_id, user_data in users.items():
                current_threshold = user_data.get("min_profit", None)
                if current_threshold is not None and current_threshold > 0.5:
                    print(f"Користувач {user_id}: поріг прибутку змінено з {current_threshold}% на 0.5%")
                    user_data["min_profit"] = 0.5
                    updated_count += 1
            
            if updated_count > 0:
                with open(config.USERS_FILE, 'w') as f:
                    json.dump(users, f, indent=4)
                print(f"Успішно оновлено {updated_count} користувачів")
            else:
                print("Не знайдено користувачів для оновлення")
        else:
            print(f"Помилка: файл {config.USERS_FILE} не знайдено")
    except Exception as e:
        print(f"Помилка при оновленні користувачів: {e}")

if __name__ == "__main__":
    update_users_thresholds()
