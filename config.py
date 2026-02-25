import os

# Пути к базе данных
SQLITE_DB_PATH = "memory/bot_database.db"

# Для обратной совместимости, если где-то используются старые переменные
USERS_DB_PATH = "memory/bot_users.json" 
CODES_DB_PATH = "memory/redemption_codes.json"

# ID, куда отправлять уведомления о новых заявках
ADMIN_NOTIFICATION_CHAT_ID = 7477930232

# Список ID менеджеров, имеющих доступ к админ-функциям
# Список ID менеджеров, имеющих доступ к админ-функциям
MANAGER_IDS = [ADMIN_NOTIFICATION_CHAT_ID]

# Настройки отображения теста
TEST_HINTS_SHOW_ALERT = True  # True - модальное окно (с кнопкой OK), False - уведомление (тост)

# Настройки Miro
MIRO_BOARD_ID = "uXjVG8Afpwo="
MIRO_ACCESS_TOKEN = os.environ.get("MIRO_ACCESS_TOKEN")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Отсутствует токен Telegram бота. Установите переменную окружения TELEGRAM_BOT_TOKEN.")