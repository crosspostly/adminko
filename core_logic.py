
import logging
from datetime import datetime, timedelta
from data_manager import get_user, update_user
from texts import TEST_QUESTIONS, TEST_HINTS
from timed_handlers import send_test_offer_job

logger = logging.getLogger(__name__)

def get_platform_user_id(user_id, platform):
    return f"{platform}_{user_id}"

async def get_or_create_user(user_id, platform, username=None, first_name=None, context=None):
    # Determine the UTM source from the context if available
    utm_source = 'direct'
    if context and context.args:
        utm_source = context.args[0]
        
    p_id = get_platform_user_id(user_id, platform)
    user_data = get_user(p_id)
    
    registration_date = datetime.now()
    bonus_added_from_link = False
    
    if not user_data:
        # Логика для абсолютно нового пользователя
        initial_bonus = 500 if utm_source == 'maps_1500' else 0
        if initial_bonus > 0:
            bonus_added_from_link = True
            schedule_retention_messages(p_id, context)
            
        user_data = {
            "user_id": p_id,
            "username": username,
            "first_name": first_name,
            "registration_date": registration_date.isoformat(),
            "phone_number": None,
            "bonus_points_initial": 1000,
            "bonus_points_current": initial_bonus,
            "bonus_expiry_date": (registration_date + timedelta(days=14)).isoformat() if initial_bonus > 0 else None,
            "bonus_given_flag": False,
            "bonus_reminders_active": True if initial_bonus > 0 else False,
            "regular_points": 0,
            "last_regular_points_accrual_date": None,
            "test_progress": 0,
            "test_answers": [0]*8,
            "crm_id": None,
            "utm_source": utm_source,
            "yandex_review_status": 'none',
            "twogis_review_status": 'none'
        }
        update_user(p_id, user_data)
        logger.info(f"New user created: {p_id} via {utm_source}")

        # Schedule the 2-hour test offer job for the new user
        context.job_queue.run_once(
            send_test_offer_job,
            when=7200, # 2 hours
            data={'user_id': p_id},
            name=f"test_offer_{p_id}"
        )
    else:
        # Логика для существующего пользователя
        # Если он перешел по ссылке карты и еще не был помечен этой акцией в БД
        if utm_source == 'maps_1500' and user_data.get('utm_source') != 'maps_1500':
            user_data['bonus_points_current'] = user_data.get('bonus_points_current', 0) + 500
            user_data['utm_source'] = 'maps_1500'
            user_data['bonus_reminders_active'] = True
            user_data['bonus_expiry_date'] = (registration_date + timedelta(days=14)).isoformat()
            update_user(p_id, user_data)
            logger.info(f"Existing user {p_id} converted to maps_1500 and received bonus.")
            bonus_added_from_link = True
            
    return user_data, bonus_added_from_link

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

async def send_retention_message_job(context):
    """Generic job to send a retention message."""
    job_data = context.job.data
    user_id = job_data['user_id']
    text = job_data['text']
    
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode='HTML')
        logger.info(f"Sent retention message to {user_id}")
    except Exception as e:
        logger.error(f"Failed to send retention message to {user_id}: {e}")

def schedule_retention_messages(user_id, context):
    """Schedules a chain of retention messages for a new user."""
    
    # Message 1: After 1 day - "Need help?"
    context.job_queue.run_once(
        send_retention_message_job, 
        when=timedelta(days=1), 
        data={'user_id': user_id, 'text': texts.RETENTION_CALLBACK_REMINDER},
        name=f"retention_1_{user_id}"
    )
    
    # Message 2: After 10 days - "Points expiring soon"
    context.job_queue.run_once(
        send_retention_message_job, 
        when=timedelta(days=10), 
        data={'user_id': user_id, 'text': texts.RETENTION_EXPIRY_REMINDER},
        name=f"retention_2_{user_id}"
    )
