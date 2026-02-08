import json
import os
from config import USERS_DB_PATH, CODES_DB_PATH

# Загрузка данных пользователей
def load_users_data():
    if not os.path.exists(USERS_DB_PATH):
        return {}
    with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

# Сохранение данных пользователей
def save_users_data(data):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(USERS_DB_PATH), exist_ok=True)
    with open(USERS_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Загрузка данных кодов
def load_codes_data():
    if not os.path.exists(CODES_DB_PATH):
        return {}
    with open(CODES_DB_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

# Сохранение данных кодов
def save_codes_data(data):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(CODES_DB_PATH), exist_ok=True)
    with open(CODES_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Функция для получения пользователя по user_id
def get_user(user_id):
    users_data = load_users_data()
    return users_data.get(str(user_id))

# Функция для сохранения/обновления пользователя
def update_user(user_id, user_data):
    users_data = load_users_data()
    users_data[str(user_id)] = user_data
    save_users_data(users_data)
