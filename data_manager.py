import sqlite3
import json
import os
from config import SQLITE_DB_PATH

DB_PATH = SQLITE_DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Функция для получения пользователя по user_id
def get_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        user_data = dict(row)
        # Преобразование типов обратно (SQLite хранит 0/1 для boolean)
        user_data["bonus_given_flag"] = bool(user_data["bonus_given_flag"])
        user_data["bonus_reminders_active"] = bool(user_data["bonus_reminders_active"])
        # Десериализация списка ответов
        try:
            user_data["test_answers"] = json.loads(user_data["test_answers"])
        except (TypeError, json.JSONDecodeError):
            user_data["test_answers"] = [0]*8
        return user_data
    return None

# Функция для сохранения/обновления пользователя
def update_user(user_id, user_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Сериализация списка ответов
    answers_str = json.dumps(user_data.get("test_answers", [0]*8))
    
    cursor.execute('''
    INSERT OR REPLACE INTO users (
        user_id, username, first_name, phone_number, registration_date,
        bonus_points_current, bonus_expiry_date, bonus_given_flag,
        bonus_reminders_active, regular_points, last_regular_points_accrual_date,
        test_progress, test_answers, crm_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(user_id),
        user_data.get("username"),
        user_data.get("first_name"),
        user_data.get("phone_number"),
        user_data.get("registration_date"),
        user_data.get("bonus_points_current", 0),
        user_data.get("bonus_expiry_date"),
        1 if user_data.get("bonus_given_flag") else 0,
        1 if user_data.get("bonus_reminders_active") else 0,
        user_data.get("regular_points", 0),
        user_data.get("last_regular_points_accrual_date"),
        user_data.get("test_progress", 0),
        answers_str,
        user_data.get("crm_id")
    ))
    conn.commit()
    conn.close()

# Загрузка данных кодов (для совместимости возвращаем словарь)
def load_codes_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM redemption_codes")
    rows = cursor.fetchall()
    conn.close()
    
    codes_dict = {}
    for row in rows:
        codes_dict[row["code"]] = dict(row)
    return codes_dict

# Сохранение данных кодов
def save_codes_data(codes_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Поскольку мы получаем весь словарь, мы обновляем записи по одной
    for code, data in codes_data.items():
        cursor.execute('''
        INSERT OR REPLACE INTO redemption_codes (
            code, user_id, generated_at, status, order_sum,
            amount_to_redeem, final_price, manager_id, manager_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            code,
            data.get("user_id"),
            data.get("generated_at"),
            data.get("status"),
            data.get("order_sum"),
            data.get("amount_to_redeem"),
            data.get("final_price"),
            data.get("manager_id"),
            data.get("manager_name")
        ))
    conn.commit()
    conn.close()

# Заглушки для старых функций (если где-то остались прямые вызовы загрузки JSON)
def load_users_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    ids = cursor.fetchall()
    conn.close()
    
    all_users = {}
    for row in ids:
        uid = row["user_id"]
        all_users[str(uid)] = get_user(uid)
    return all_users

def save_users_data(data):
    for uid, udata in data.items():
        update_user(int(uid), udata)
