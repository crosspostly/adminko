import random
import string
from datetime import datetime
from config import MANAGER_IDS

# Функция для генерации одноразового кода
def generate_redeem_code(length=6):
    characters = string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def is_manager(user_id):
    return user_id in MANAGER_IDS


# Вспомогательная функция для форматирования даты
def format_date_for_ru(iso_date_str):
    if not iso_date_str:
        return "не определена"
    date_obj = datetime.fromisoformat(iso_date_str)
    months_ru = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
        7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    day = date_obj.day
    month = months_ru[date_obj.month]
    return f"{day:02d} {month}"
