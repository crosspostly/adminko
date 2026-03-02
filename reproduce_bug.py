
import json
import sqlite3
import os

DB_PATH = "memory/bot_database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        user_data = dict(row)
        user_data["test_answers"] = json.loads(user_data["test_answers"])
        return user_data
    return None

def update_user(user_id, user_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    answers_str = json.dumps(user_data.get("test_answers", [0]*8))
    cursor.execute('''
    INSERT OR REPLACE INTO users (
        user_id, username, first_name, phone_number, registration_date,
        bonus_points_current, bonus_expiry_date, bonus_given_flag,
        bonus_reminders_active, regular_points, last_regular_points_accrual_date,
        test_progress, test_answers
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, user_data.get("username"), user_data.get("first_name"),
        user_data.get("phone_number"), user_data.get("registration_date"),
        user_data.get("bonus_points_current", 0), user_data.get("bonus_expiry_date"),
        1 if user_data.get("bonus_given_flag") else 0,
        1 if user_data.get("bonus_reminders_active") else 0,
        user_data.get("regular_points", 0), user_data.get("last_regular_points_accrual_date"),
        user_data.get("test_progress", 0), answers_str
    ))
    conn.commit()
    conn.close()

def simulate_test(user_id):
    print(f"Simulating test for user {user_id}")
    user_data = get_user(user_id)
    if not user_data:
        user_data = {
            "user_id": user_id,
            "test_progress": 0,
            "test_answers": [0]*8,
            "bonus_given_flag": False
        }
        update_user(user_id, user_data)
    
    for i in range(8):
        print(f"  Answering question {i}...")
        user_data = get_user(user_id)
        # Simulation of handle_test_answer
        question_index = i
        if question_index != user_data["test_progress"]:
            print(f"    ERROR: index mismatch! {question_index} != {user_data['test_progress']}")
            return
        
        user_data["test_answers"][question_index] = 1
        user_data["test_progress"] += 1
        update_user(user_id, user_data)
        print(f"    Progress updated to {user_data['test_progress']}")

    # Simulation of show_test_results
    user_data = get_user(user_id)
    print(f"  Test completed. Results: {sum(user_data['test_answers'])}")
    user_data["test_progress"] = 0
    user_data["test_answers"] = [0]*8
    user_data["bonus_given_flag"] = True
    update_user(user_id, user_data)
    print("  Progress reset.")

if __name__ == "__main__":
    simulate_test(999999)
