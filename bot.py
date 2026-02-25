import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Импорты для рефакторинга
import config
import handlers
import admin_handlers

# Устанавливаем базовую конфигурацию логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Callback function to set up the bot after it has been initialized."""
    # Установка команд в меню Telegram
    await application.bot.set_my_commands([
        ("start", "Начать взаимодействие с ботом"),
        # ("about", "Информация о нашей компании"), # Удалена после объединения с контактами
        ("menu", "Список наших услуг"),
        ("contact", "Контакты и о нас"), # Изменено название
        ("cabinet", "Личный кабинет")
        # admin_redeem_points удалена из публичных команд
    ])

def main() -> None:
    """Start the bot."""
    # Используйте токен вашего бота
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен в переменных окружения.")
        raise ValueError("Отсутствует токен Telegram бота.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Добавление обработчиков команд
    application.add_handler(CommandHandler("start", handlers.start))
    # application.add_handler(CommandHandler("about", about_us)) # Удалена после объединения с контактами
    application.add_handler(CommandHandler("menu", handlers.our_services))
    application.add_handler(CommandHandler("contact", handlers.contact_us))
    application.add_handler(CommandHandler("cabinet", handlers.personal_account))
    application.add_handler(CommandHandler("expmin", handlers.reset_test_status))
    application.add_handler(CommandHandler("admin_redeem_points", admin_handlers.admin_redeem_points_start))

    # Добавление обработчиков CallbackQuery (для inline-кнопок)
    application.add_handler(CallbackQueryHandler(handlers.start, pattern='^start_menu_main$'))  # Для возврата в главное меню
    application.add_handler(CallbackQueryHandler(handlers.ask_question, pattern='^start_test$'))
    application.add_handler(CallbackQueryHandler(handlers.handle_test_answer, pattern='^test_answer_'))
    application.add_handler(CallbackQueryHandler(handlers.next_question, pattern='^next_question_'))  # Для перехода к следующему вопросу
    application.add_handler(CallbackQueryHandler(handlers.show_test_results, pattern='^show_test_results$'))  # Для показа результатов теста
    application.add_handler(CallbackQueryHandler(handlers.order_diagnostic_menu, pattern='^order_diagnostic_menu$'))
    application.add_handler(CallbackQueryHandler(handlers.personal_account, pattern='^personal_account_menu$'))
    application.add_handler(CallbackQueryHandler(handlers.use_points_start, pattern='^use_points_start$'))
    application.add_handler(CallbackQueryHandler(admin_handlers.send_client_confirm, pattern='^send_client_confirm$'))
    application.add_handler(CallbackQueryHandler(admin_handlers.confirm_redeem, pattern='^confirm_redeem_'))
    application.add_handler(CallbackQueryHandler(admin_handlers.cancel_redeem_admin, pattern='^cancel_redeem_admin$'))
    application.add_handler(CallbackQueryHandler(admin_handlers.cancel_redeem_client, pattern='^cancel_redeem_client_'))
    application.add_handler(CallbackQueryHandler(handlers.our_services, pattern='^our_services_menu$'))  # Для кнопок в разделах
    application.add_handler(CallbackQueryHandler(handlers.contact_us, pattern='^contact_us_menu$'))  # Для кнопок в разделах
    application.add_handler(CallbackQueryHandler(handlers.request_phone_number_menu, pattern='^request_callback$')) # Для кнопки "Связаться с нами"
    # application.add_handler(CallbackQueryHandler(about_us, pattern='^about_us_menu$')) # Удалена после объединения с контактами
    application.add_handler(CallbackQueryHandler(handlers.service_repair_pc_notebooks_menu, pattern='^service_repair_pc_notebooks$')) # Для ремонта ПК/ноутбуков
    application.add_handler(CallbackQueryHandler(handlers.service_it_support_orgs_menu, pattern='^service_it_support_orgs$')) # Для IT-обслуживания организаций
    application.add_handler(CallbackQueryHandler(handlers.service_video_surveillance_menu, pattern='^service_video_surveillance$')) # Для монтажа видеонаблюдения

    # Добавление обработчиков сообщений
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY & ~filters.COMMAND, admin_handlers.handle_manager_input))  # Для ответов менеджера
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_phone_number_input))  # Для ручного ввода номера (включая проверку формата)
    application.add_handler(MessageHandler(filters.CONTACT & ~filters.COMMAND, handlers.handle_contact_share)) # Для кнопки "Поделиться номером"

    # Запуск бота в режиме long polling (для удобства тестирования)
    # Для вебхуков нужна дополнительная настройка, которая зависит от окружения
    logger.info("Бот запускается в режиме Long Polling.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()