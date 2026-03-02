import random
import string
from datetime import datetime
from config import MANAGER_IDS
import re
import html
from fuzzywuzzy import fuzz # Для нечеткого сравнения

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

def clean_miro_text(text):
    """
    Очищает текст Miro для Telegram:
    1. Конвертирует <p> и <br> в переносы строк.
    2. Оставляет только разрешенные теги (b, i, u, s, a, code).
    3. Декодирует HTML-сущности.
    """
    if not text:
        return ""
    
    # Заменяем структурные теги на переносы строк
    text = text.replace('<p>', '').replace('</p>', '\n')
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = text.replace('&nbsp;', ' ')

    # Список разрешенных тегов Telegram
    # Удаляем все теги, кроме b, i, u, s, a, code, strong, em, ins, strike, del
    allowed = r'(/?(b|i|u|s|a|code|strong|em|ins|strike|del)(?=>|\\s))'
    text = re.sub(r'<(?!' + allowed + r')[^>]+>', '', text)

    # Декодируем сущности (смайлики, спецсимволы)
    text = html.unescape(text)
    
    # Убираем лишние пробелы и множественные переносы в конце
    text = text.strip()
    text = re.sub(r'\\n{3,}', '\\n\\n', text)
    
    return text

def extract_tag(text):
    """Извлекает технический тег типа {#VAR} из начала текста."""
    match = re.match(r'\{#([A-Z_]+)\}', text)
    if match:
        return match.group(1), text[match.end():].strip() # Возвращает тег и очищенный текст
    return None, text

def fuzzy_match(text1, text2, threshold=70): # Понизим порог для большей гибкости
    """Сравнивает две строки с использованием нечеткого сравнения (fuzzywuzzy)."""
    if not text1 or not text2:
        return False
    
    # Используем token_set_ratio, который лучше обрабатывает перестановки слов и частичные совпадения
    ratio = fuzz.token_set_ratio(clean_miro_text(text1).lower(), clean_miro_text(text2).lower())
    return ratio >= threshold
