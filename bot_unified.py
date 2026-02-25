import asyncio
import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters,
    Application
)
from maxapi import Bot, Dispatcher
import handlers
import max_handlers
import admin_handlers
import config

# Устанавливаем базовую конфигурацию логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def post_init_tg(application: Application):
    """Callback function to set up the bot after it has been initialized."""
    await application.bot.set_my_commands([
        ("start", "Начать взаимодействие с ботом"),
        ("menu", "Список наших услуг"),
        ("contact", "Контакты и о нас"),
        ("cabinet", "Личный кабинет")
    ])

async def run_telegram():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не установлен в переменных окружения.")
        return
    
    application = ApplicationBuilder().token(token).post_init(post_init_tg).build()

    # Команды
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("menu", handlers.our_services))
    application.add_handler(CommandHandler("contact", handlers.contact_us))
    application.add_handler(CommandHandler("cabinet", handlers.personal_account))
    application.add_handler(CommandHandler("expmin", handlers.reset_test_status))
    application.add_handler(CommandHandler("admin_redeem_points", admin_handlers.admin_redeem_points_start))

    # CallbackQuery
    application.add_handler(CallbackQueryHandler(handlers.start, pattern='^start_menu_main$'))
    application.add_handler(CallbackQueryHandler(handlers.ask_question, pattern='^start_test$'))
    application.add_handler(CallbackQueryHandler(handlers.handle_test_answer, pattern='^test_answer_'))
    application.add_handler(CallbackQueryHandler(handlers.next_question, pattern='^next_question_'))
    application.add_handler(CallbackQueryHandler(handlers.show_test_results, pattern='^show_test_results$'))
    application.add_handler(CallbackQueryHandler(handlers.order_diagnostic_menu, pattern='^order_diagnostic_menu$'))
    application.add_handler(CallbackQueryHandler(handlers.personal_account, pattern='^personal_account_menu$'))
    application.add_handler(CallbackQueryHandler(handlers.use_points_start, pattern='^use_points_start$'))
    application.add_handler(CallbackQueryHandler(admin_handlers.send_client_confirm, pattern='^send_client_confirm$'))
    application.add_handler(CallbackQueryHandler(admin_handlers.confirm_redeem, pattern='^confirm_redeem_'))
    application.add_handler(CallbackQueryHandler(admin_handlers.cancel_redeem_admin, pattern='^cancel_redeem_admin$'))
    application.add_handler(CallbackQueryHandler(admin_handlers.cancel_redeem_client, pattern='^cancel_redeem_client_'))
    application.add_handler(CallbackQueryHandler(handlers.our_services, pattern='^our_services_menu$'))
    application.add_handler(CallbackQueryHandler(handlers.contact_us, pattern='^contact_us_menu$'))
    application.add_handler(CallbackQueryHandler(handlers.request_phone_number_menu, pattern='^request_callback$'))
    application.add_handler(CallbackQueryHandler(handlers.service_repair_pc_notebooks_menu, pattern='^service_repair_pc_notebooks$'))
    application.add_handler(CallbackQueryHandler(handlers.service_it_support_orgs_menu, pattern='^service_it_support_orgs$'))
    application.add_handler(CallbackQueryHandler(handlers.service_video_surveillance_menu, pattern='^service_video_surveillance$'))

    # Сообщения
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY & ~filters.COMMAND, admin_handlers.handle_manager_input))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_phone_number_input))
    application.add_handler(MessageHandler(filters.CONTACT & ~filters.COMMAND, handlers.handle_contact_share))

    logger.info("[+] Telegram Bot starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Чтобы корутина не завершалась
    while True:
        await asyncio.sleep(3600)

async def run_max():
    token = os.environ.get("MAX_BOT_TOKEN")
    if not token:
        logger.warning("MAX_BOT_TOKEN не установлен. Бот MAX пропущен.")
        return

    bot = Bot(token=token)
    dp = Dispatcher()
    
    # Регистрация хендлеров MAX
    dp.message.register(max_handlers.cmd_start, commands=["start"])
    dp.message_callback.register(max_handlers.handle_callback)
    
    logger.info("[+] MAX Bot starting...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in MAX Bot: {e}")

async def main():
    await asyncio.gather(
        run_telegram(),
        run_max()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bots stopped.")
