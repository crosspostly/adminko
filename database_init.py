import sqlite3
import json
import os
from datetime import datetime
from config import USERS_DB_PATH

DB_PATH = "memory/bot_database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database with the required tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица пользователей (основные данные и баланс)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        phone_number TEXT,
        registration_date TEXT,
        bonus_points_current REAL DEFAULT 0,
        bonus_expiry_date TEXT,
        bonus_given_flag INTEGER DEFAULT 0,
        bonus_reminders_active INTEGER DEFAULT 0,
        regular_points REAL DEFAULT 0,
        last_regular_points_accrual_date TEXT,
        test_progress INTEGER DEFAULT 0,
        test_answers TEXT -- Храним как JSON-строку [0,1,0...]
    )
    ''')
    
    # Таблица кодов списания (история транзакций)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS redemption_codes (
        code TEXT PRIMARY KEY,
        user_id INTEGER,
        generated_at TEXT,
        status TEXT, -- pending, used, canceled_by_manager, canceled_by_client
        order_sum REAL,
        amount_to_redeem REAL,
        final_price REAL,
        manager_id INTEGER,
        manager_name TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def migrate_from_json():
    """Migrates data from existing JSON files to SQLite."""
    init_db()
    
    # 1. Migrate Users
    if os.path.exists(USERS_DB_PATH):
        with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for str_id, data in users_data.items():
            answers_str = json.dumps(data.get("test_answers", [0]*8))
            cursor.execute('''
            INSERT OR REPLACE INTO users (
                user_id, username, first_name, phone_number, registration_date,
                bonus_points_current, bonus_expiry_date, bonus_given_flag,
                bonus_reminders_active, regular_points, last_regular_points_accrual_date,
                test_progress, test_answers
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                int(str_id), data.get("username"), data.get("first_name"),
                data.get("phone_number"), data.get("registration_date"),
                data.get("bonus_points_current", 0), data.get("bonus_expiry_date"),
                1 if data.get("bonus_given_flag") else 0,
                1 if data.get("bonus_reminders_active") else 0,
                data.get("regular_points", 0), data.get("last_regular_points_accrual_date"),
                data.get("test_progress", 0), answers_str
            ))
        conn.commit()
        conn.close()
        print(f"Successfully migrated {len(users_data)} users.")

    # 2. Migrate Codes
    from config import CODES_DB_PATH
    if os.path.exists(CODES_DB_PATH):
        with open(CODES_DB_PATH, 'r', encoding='utf-8') as f:
            codes_data = json.load(f)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for code, data in codes_data.items():
            cursor.execute('''
            INSERT OR REPLACE INTO redemption_codes (
                code, user_id, generated_at, status, order_sum,
                amount_to_redeem, final_price, manager_id, manager_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                code, data.get("user_id"), data.get("generated_at"),
                data.get("status"), data.get("order_sum"),
                data.get("amount_to_redeem"), data.get("final_price"),
                data.get("manager_id"), data.get("manager_name")
            ))
        conn.commit()
        conn.close()
        print(f"Successfully migrated {len(codes_data)} codes.")

if __name__ == "__main__":
    migrate_from_json()
