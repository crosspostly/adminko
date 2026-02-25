
import logging
from datetime import datetime, timedelta
from data_manager import get_user, update_user
from texts import TEST_QUESTIONS, TEST_HINTS

logger = logging.getLogger(__name__)

def get_platform_user_id(user_id, platform):
    return f"{platform}_{user_id}"

async def get_or_create_user(user_id, platform, username=None, first_name=None):
    p_id = get_platform_user_id(user_id, platform)
    user_data = get_user(p_id)
    
    if not user_data:
        registration_date = datetime.now()
        user_data = {
            "user_id": p_id,
            "username": username,
            "first_name": first_name,
            "registration_date": registration_date.isoformat(),
            "phone_number": None,
            "bonus_points_initial": 1000,
            "bonus_points_current": 0,
            "bonus_expiry_date": None,
            "bonus_given_flag": False,
            "bonus_reminders_active": False,
            "regular_points": 0,
            "last_regular_points_accrual_date": None,
            "test_progress": 0,
            "test_answers": [0]*8
        }
        update_user(p_id, user_data)
    return user_data

def process_test_answer(user_data, question_index, answer):
    """
    Обрабатывает ответ, возвращает (is_correct_index, next_index, hint, is_finished)
    """
    current_progress = user_data["test_progress"]
    
    # Защита от старых нажатий
    if question_index != current_progress:
        return False, current_progress, None, False
    
    # 'Не знаю' (2) обрабатываем как 'Нет' (0)
    final_answer = 1 if answer == 1 else 0
    
    user_data["test_answers"][question_index] = final_answer
    user_data["test_progress"] += 1
    
    hint = TEST_HINTS[question_index]
    is_finished = user_data["test_progress"] >= len(TEST_QUESTIONS)
    
    return True, user_data["test_progress"], hint, is_finished

def calculate_results(user_data):
    positive_answers = sum(user_data.get("test_answers", [0]*8))
    
    bonus_added = False
    if not user_data.get("bonus_given_flag"):
        user_data["bonus_points_current"] = user_data.get("bonus_points_initial", 1000)
        user_data["bonus_given_flag"] = True
        user_data["bonus_reminders_active"] = True
        # Устанавливаем дату истечения: +14 дней
        expiry_date = datetime.now() + timedelta(days=14)
        user_data["bonus_expiry_date"] = expiry_date.isoformat()
        bonus_added = True
        
    return positive_answers, bonus_added, user_data
