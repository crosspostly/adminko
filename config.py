import os

# Пути к файлам базы данных
USERS_DB_PATH = "memory/bot_users.json"
CODES_DB_PATH = "memory/redemption_codes.json"

# Список вопросов для теста
TEST_QUESTIONS = [
    {"text": "Ваш компьютер стал заметно медленнее загружать файлы или программы, и вы слышите необычные шумы (гул, треск, щелчки) от жесткого диска?"},
    {"text": "Вентиляторы компьютера гудят громче обычного, а сам ПК часто перегревается (горячий на ощупь), даже при небольших нагрузках?"},
    {"text": 'На экране монитора регулярно появляются полосы, искажения, "глюки" или внезапно пропадает изображение, особенно во время работы или игр?'},
    {"text": 'Система часто "зависает", работает с заметными задержками, а программы запускаются нестабильно или не с первого раза, даже после перезагрузки?'},
    {"text": 'На вашем компьютере периодически появляются "синие экраны смерти" (BSOD) с кодами ошибок, особенно при высокой нагрузке или запуске требовательных приложений?'},
    {"text": "Компьютер самопроизвольно выключается или перезапускается без предупреждения, иногда даже при просмотре видео или работе в браузере?"},
    {"text": "При включении компьютера вы слышите короткие или длинные звуковые сигналы (пищание) из системного блока, и ПК не загружается нормально?"},
    {"text": "На вашем компьютере самостоятельно запускаются программы, открываются окна с рекламой, или вы замечаете появление новых, вами не устанавливаемых приложений?"},
]


# ID, куда отправлять уведомления о новых заявках (пока ваш ID)
ADMIN_NOTIFICATION_CHAT_ID = 7477930232

MANAGER_IDS = []

MANAGER_IDS_ENV = os.environ.get("MANAGER_IDS")
if MANAGER_IDS_ENV:
    try:
        MANAGER_IDS = [int(item.strip()) for item in MANAGER_IDS_ENV.split(",") if item.strip().isdigit()]
    except ValueError:
        MANAGER_IDS = []

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def setup_logging():
    """Настройка структурированного логирования."""
    import logging
    import sys
    from datetime import datetime

    os.makedirs('logs', exist_ok=True)

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
