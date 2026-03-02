from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply
from telegram.ext import ContextTypes
import logging

from data_manager import get_user, update_user, load_codes_data, save_codes_data
from config import ADMIN_NOTIFICATION_CHAT_ID, TEST_HINTS_SHOW_ALERT, MANAGER_IDS
from texts import *
from utils import generate_redeem_code, format_date_for_ru, is_manager
import core_logic
import review_handlers

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    user_data, bonus_added_from_link = await core_logic.get_or_create_user(
        user_id, 
        platform="TG", 
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        context=context
    )

    # If a bonus was added via deep link, notify the user first and then stop
    if bonus_added_from_link:
        keyboard_bonus = [
            [InlineKeyboardButton("Помощь специалиста 📞", callback_data='request_callback')],
            [InlineKeyboardButton("👤 Личный кабинет", callback_data='personal_account_menu')]
        ]
        reply_markup_bonus = InlineKeyboardMarkup(keyboard_bonus)
        await update.message.reply_text(
            DEEPLINK_BONUS_NOTIFICATION, 
            reply_markup=reply_markup_bonus, 
            parse_mode='HTML'
        )
        return  # Stop further processing for deep link users


    if not user_data["bonus_given_flag"]:
        text = START_NEW_USER if user_data.get("registration_date") else START_RETURNING_USER_NO_BONUS
    else:
        text = START_COMPLETED_TEST

    keyboard = []
    if not user_data["bonus_given_flag"]:
        keyboard.append([InlineKeyboardButton("🚀 Начать Экспресс-тест", callback_data='start_test')])

    keyboard.append([InlineKeyboardButton("💼 Наши услуги", callback_data='our_services_menu')])
    keyboard.append([InlineKeyboardButton("👤 Личный кабинет", callback_data='personal_account_menu')])
    keyboard.append([InlineKeyboardButton("ℹ️ Контакты", callback_data='contact_us_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def reset_test_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /expmin - сбрасывает статус прохождения теста для пользователя.
    Позволяет пройти тест заново и снова получить кнопку в меню.
    """
    user_id = update.effective_user.id
    p_id = f"TG_{user_id}"
    user_data = get_user(p_id)
    
    if user_data:
        user_data["bonus_given_flag"] = False
        user_data["test_progress"] = 0
        user_data["test_answers"] = [0]*8
        # Мы НЕ обнуляем накопленные баллы (regular_points), 
        # но бонусные (bonus_points_current) сбрасываем, чтобы начислить их заново после теста.
        user_data["bonus_points_current"] = 0
        user_data["bonus_expiry_date"] = None
        
        update_user(p_id, user_data)
        await update.message.reply_text("✅ Статус теста сброшен! Теперь вы можете пройти его заново через команду /start.")
    else:
        await update.message.reply_text("Пользователь не найден. Введите /start для регистрации.")


async def our_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Определяем, был ли вызов через команду или CallbackQuery
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()
        message_editor = query.edit_message_text
    else:
        user_id = update.effective_user.id
        message_editor = update.message.reply_text

    p_id = f"TG_{user_id}"
    user_data = get_user(p_id)
    
    bonus_reminder_text = ""
    if user_data and user_data.get("bonus_given_flag") and user_data.get("bonus_points_current", 0) > 0:
        expiry_date_str = user_data.get("bonus_expiry_date")
        if expiry_date_str and datetime.fromisoformat(expiry_date_str) > datetime.now():
            bonus_reminder_text = (
                f"\n\n✨ Напоминаем: у вас есть **{user_data['bonus_points_current']} бонусных рублей** до "
                f"**{format_date_for_ru(expiry_date_str)}**!"
            )

    text = OUR_SERVICES_TITLE + bonus_reminder_text
    keyboard = [
        [InlineKeyboardButton("Ремонт ПК/Ноутбуков 💻", callback_data='service_repair_pc_notebooks')],
        [InlineKeyboardButton("Системное администрирование 🏢", callback_data='service_it_support_orgs')],
        [InlineKeyboardButton("Видеонаблюдение, СКС, СКУД 📹", callback_data='service_video_surveillance')],
        [InlineKeyboardButton("Контакты ℹ️", callback_data='contact_us_menu'), InlineKeyboardButton("В меню 🏡", callback_data='start_menu_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message_editor(text, reply_markup=reply_markup, parse_mode='HTML')

async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message_editor = query.edit_message_text
    else:
        message_editor = update.message.reply_text

    text = CONTACT_US_TITLE + CONTACT_US_TEXT
    keyboard = [
        [InlineKeyboardButton("↩️ Главное меню", callback_data='start_menu_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message_editor(text, reply_markup=reply_markup, parse_mode='HTML', disable_web_page_preview=True)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE, answered: bool = False) -> None:
    query = update.callback_query
    if not answered:
        await query.answer()

    user_id = query.from_user.id
    p_id = f"TG_{user_id}"
    user_data = get_user(p_id)
    if user_data is None:
        await query.edit_message_text("Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    current_question_index = user_data["test_progress"]

    if current_question_index >= len(TEST_QUESTIONS):
        await show_test_results(update, context, answered=True)
        return

    question_text = TEST_QUESTIONS[current_question_index]["text"]
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data=f'test_answer_{current_question_index}_1'),
            InlineKeyboardButton("Нет", callback_data=f'test_answer_{current_question_index}_0'),
            InlineKeyboardButton("Не знаю", callback_data=f'test_answer_{current_question_index}_2')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(
            f"Вопрос {current_question_index + 1}/8: {question_text}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")

async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    p_id = f"TG_{user_id}"
    user_data = get_user(p_id)
    if user_data is None:
        await query.edit_message_text("Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    try:
        _, _, question_index_str = query.data.split('_')
        question_index = int(question_index_str)
        user_data["test_progress"] = question_index
        update_user(p_id, user_data)
        await ask_question(update, context, answered=True)
    except Exception as e:
        logger.error(f"Error in next_question: {e}")

async def handle_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    p_id = f"TG_{user_id}"
    user_data = get_user(p_id)
    if user_data is None:
        await query.answer(show_alert=True, text="Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    try:
        _, _, question_index_str, answer_str = query.data.split('_')
        question_index = int(question_index_str)
        answer = int(answer_str)
        
        success, next_progress, hint_text, is_finished = core_logic.process_test_answer(user_data, question_index, answer)
        
        if not success:
            # Пользователь ответил на старый вопрос или на вопрос из другого сеанса
            # Показываем актуальный вопрос, чтобы он не застрял
            await query.answer(show_alert=False, text="Показываю актуальный вопрос...")
            await ask_question(update, context, answered=True)
            return

        update_user(p_id, user_data)

        # Показываем подсказку после ответа (всплывающее окно)
        if not is_finished:
            # Ещё есть вопросы — показываем подсказку и автоматически переходим к следующему
            await query.answer(show_alert=TEST_HINTS_SHOW_ALERT, text=hint_text)
            await ask_question(update, context, answered=True)
        else:
            # Тест завершён — показываем подсказку и автоматически переходим к результатам
            await query.answer(show_alert=TEST_HINTS_SHOW_ALERT, text=hint_text)
            await show_test_results(update, context, answered=True)
    except Exception as e:
        logger.error(f"Error in handle_test_answer: {e}")
        await query.answer(show_alert=True, text="Произошла ошибка при обработке ответа.")

async def show_test_results(update: Update, context: ContextTypes.DEFAULT_TYPE, answered: bool = False) -> None:
    query = update.callback_query
    if not answered:
        await query.answer()

    user_id = query.from_user.id
    p_id = f"TG_{user_id}"
    user_data = get_user(p_id)
    if user_data is None:
        await query.edit_message_text("Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    try:
        logger.info(f"Calculating results for {p_id}")
        positive_answers, bonus_added, user_data = core_logic.calculate_results(user_data)
        
        result_text = TEST_RESULTS_PROBLEM_COUNT.format(count=positive_answers)

        if 0 <= positive_answers <= 1:
            result_text += TEST_RESULTS_0_1
        elif 2 <= positive_answers <= 4:
            result_text += TEST_RESULTS_2_4
        elif 5 <= positive_answers <= 8:
            result_text += TEST_RESULTS_5_8

        bonus_info_text = ""
        if bonus_added:
            expiry_date = user_data.get('bonus_expiry_date')
            expiry_str = format_date_for_ru(expiry_date) if expiry_date else "неизвестно"
            bonus_info_text = TEST_RESULTS_BONUS_NEW.format(
                expiry_date=expiry_str
            )
        elif user_data.get("bonus_given_flag") and user_data.get("bonus_points_current", 0) > 0:
            expiry_date_str = user_data.get("bonus_expiry_date")
            if expiry_date_str:
                try:
                    expiry_dt = datetime.fromisoformat(expiry_date_str)
                    if expiry_dt > datetime.now():
                        bonus_info_text = TEST_RESULTS_BONUS_EXISTING.format(
                            points=user_data['bonus_points_current'],
                            expiry_date=format_date_for_ru(expiry_date_str)
                        )
                except Exception as date_err:
                    logger.error(f"Date parsing error for {p_id}: {date_err}")

        text = TEST_RESULTS_INTRO + result_text + bonus_info_text
        keyboard = [
            [InlineKeyboardButton("Заказать бесплатную диагностику 🛠️", callback_data='order_diagnostic_menu')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

        # Сброс прогресса теста в любом случае после показа результатов
        user_data["test_progress"] = 0
        user_data["test_answers"] = [0]*8
        update_user(p_id, user_data)
        logger.info(f"Results shown and progress reset for {p_id}")
    except Exception as e:
        logger.error(f"CRITICAL Error in show_test_results for {p_id}: {e}", exc_info=True)
        # При ошибке все равно пытаемся сбросить прогресс, чтобы пользователь не застрял
        user_data["test_progress"] = 0
        update_user(p_id, user_data)
        await query.edit_message_text("Произошла ошибка при показе результатов. Пожалуйста, попробуйте снова /start.")

async def order_diagnostic_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    p_id = f"TG_{user_id}"
    user_data = get_user(p_id)
    
    first_name = query.from_user.first_name if query.from_user.first_name else "пользователь"

    bonus_reminder_text = ""
    if user_data and user_data["bonus_given_flag"] and user_data["bonus_points_current"] > 0 and datetime.fromisoformat(user_data["bonus_expiry_date"]) > datetime.now():
        bonus_reminder_text = (
            f"\n\nНапоминаем, что у вас есть **{user_data['bonus_points_current']} рублей** на счету, " +
            f"которые вы можете использовать для оплаты диагностики или других услуг до " +
            f"**{format_date_for_ru(user_data['bonus_expiry_date'])}**."
        )

    # Используем DIAGNOSTIC_REQUEST_TEXT с подстановкой имени
    text = DIAGNOSTIC_REQUEST_TEXT.format(first_name=first_name) + bonus_reminder_text

    keyboard = [
        [InlineKeyboardButton("Связаться с нами 📞", callback_data='request_callback')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def request_phone_number_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    first_name = query.from_user.first_name if query.from_user.first_name else "пользователь"

    text = REQUEST_PHONE_NUMBER_TEXT.format(first_name=first_name)
    
    keyboard = [
        [KeyboardButton("Поделиться номером телефона 📞", request_contact=True)],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    # Убираем инлайн-клавиатуру из предыдущего сообщения
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Отправляем новое сообщение с Reply-клавиатурой
    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)
    
    context.user_data['state'] = 'awaiting_phone_number' # Устанавливаем состояние ожидания номера

async def handle_phone_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('state') != 'awaiting_phone_number':
        return # Игнорируем, если не ждем номер телефона

    user_id = update.effective_user.id
    p_id = f"TG_{user_id}"
    user_data = get_user(p_id) # Assume get_user is available in bot.py
    if user_data:
        user_data["phone_number"] = phone_number
        update_user(p_id, user_data) # Assume update_user is available in bot.py
        
        bonus_reminder_text = ""
        if user_data and user_data["bonus_given_flag"] and user_data["bonus_points_current"] > 0 and datetime.fromisoformat(user_data["bonus_expiry_date"]) > datetime.now():
            bonus_reminder_text = (
                f"\n\nНапоминаем, что у вас есть **{user_data['bonus_points_current']} рублей** на счету, " +
                f"которые вы можете использовать для оплаты диагностики или других услуг до " +
                f"**{format_date_for_ru(user_data['bonus_expiry_date'])}**."
            )

        text = PHONE_RECEIVED_CONFIRMATION.format(first_name=first_name, phone_number=phone_number) + bonus_reminder_text

        await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        context.user_data['state'] = None
        
        admin_message = ADMIN_NEW_CALLBACK_REQUEST.format(
            first_name=first_name,
            user_id=user_id,
            username=username,
            phone_number=phone_number
        )
        await context.bot.send_message(chat_id=ADMIN_NOTIFICATION_CHAT_ID, text=admin_message, parse_mode='HTML')
    else:
        await update.message.reply_text("Произошла ошибка. Пожалуйста, начните с команды /start.", reply_markup=ReplyKeyboardRemove())


async def handle_contact_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('state') != 'awaiting_phone_number':
        return # Игнорируем, если не ждем номер телефона

    user_id = update.effective_user.id
    p_id = f"TG_{user_id}"
    phone_number = update.message.contact.phone_number
    first_name = update.effective_user.first_name if update.effective_user.first_name else "Неизвестный"
    username = update.effective_user.username if update.effective_user.username else ""

    user_data = get_user(p_id) # Assume get_user is available in bot.py
    if user_data:
        user_data["phone_number"] = phone_number
        update_user(p_id, user_data) # Assume update_user is available in bot.py
        
        bonus_reminder_text = ""
        if user_data and user_data["bonus_given_flag"] and user_data["bonus_points_current"] > 0 and datetime.fromisoformat(user_data["bonus_expiry_date"]) > datetime.now():
            bonus_reminder_text = (
                f"\n\nНапоминаем, что у вас есть **{user_data['bonus_points_current']} рублей** на счету, " +
                f"которые вы можете использовать для оплаты диагностики или других услуг до " +
                f"**{format_date_for_ru(user_data['bonus_expiry_date'])}**."
            )

        text = PHONE_RECEIVED_CONFIRMATION.format(first_name=first_name, phone_number=phone_number) + bonus_reminder_text

        await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        context.user_data['state'] = None # Сбрасываем состояние

        admin_message = ADMIN_NEW_CALLBACK_REQUEST.format(
            first_name=first_name,
            user_id=user_id,
            username=username,
            phone_number=phone_number
        )
        await context.bot.send_message(chat_id=ADMIN_NOTIFICATION_CHAT_ID, text=admin_message, parse_mode='HTML')
    else:
        await update.message.reply_text("Произошла ошибка. Пожалуйста, начните с команды /start.", reply_markup=ReplyKeyboardRemove())

async def personal_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Определяем, был ли вызов через команду или CallbackQuery
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        first_name = query.from_user.first_name
        await query.answer() # Отвечаем на CallbackQuery
        message_editor = query.edit_message_text
    else:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        message_editor = update.message.reply_text

    p_id = f"TG_{user_id}"
    user_data = get_user(p_id)

    if not user_data:
        # Если это CallbackQuery, отвечаем через edit_message_text
        if update.callback_query:
            await update.callback_query.edit_message_text(CABINET_NO_USER_ERROR)
        else:
            await update.message.reply_text(CABINET_NO_USER_ERROR)
        return

    bonus_info = ""
    if user_data.get("bonus_points_current", 0) > 0 and user_data.get("bonus_expiry_date") and datetime.fromisoformat(user_data["bonus_expiry_date"]) > datetime.now():
        bonus_info = CABINET_POINTS_INFO.format(
            points=user_data['bonus_points_current'],
            expiry_date=format_date_for_ru(user_data['bonus_expiry_date'])
        )

    regular_info = ""
    # if user_data["regular_points"] > 0:
    #     regular_info = f"   • Накоплено баллов: **{user_data['regular_points']} руб.**\n"

    keyboard = []

    if not bonus_info and not regular_info:
        balance_text = CABINET_NO_POINTS
    else:
        balance_text = CABINET_HAS_POINTS_TITLE + bonus_info + regular_info + CABINET_USE_POINTS_PROMPT
        keyboard.append([InlineKeyboardButton("Использовать баллы", callback_data='use_points_start')])

    keyboard.append([InlineKeyboardButton("Вернуться в главное меню 🏡", callback_data='start_menu_main')])

    final_text = f"Привет, {first_name}! Это ваш Личный кабинет.\n\n{balance_text}"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message_editor(
        final_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def use_points_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    p_id = f"TG_{user_id}"
    user_data = get_user(p_id)

    if not user_data or (user_data["bonus_points_current"] == 0 and user_data["regular_points"] == 0):
        await query.edit_message_text(USE_POINTS_NO_POINTS, parse_mode='HTML')
        return

    # Генерация кода для пользователя
    code = generate_redeem_code()
    codes_data = load_codes_data()
    codes_data[code] = {
        "user_id": user_id,
        "generated_at": datetime.now().isoformat(),
        "status": "pending",
        "amount_to_redeem": user_data["bonus_points_current"] + user_data["regular_points"],
        "order_sum": None,
        "manager_id": None,
        "final_price": None
    }
    save_codes_data(codes_data)

    text = USE_POINTS_CODE_GENERATED.format(code=code)
    keyboard = [
        [InlineKeyboardButton("Заказать обратный звонок 📞", callback_data='request_callback')],
        [InlineKeyboardButton("Вернуться в Личный кабинет", callback_data='personal_account_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


# НОВЫЕ ФУНКЦИИ ДЛЯ КАТЕГОРИЙ УСЛУГ
async def service_repair_pc_notebooks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = SERVICE_REPAIR_PC_NOTEBOOKS_TITLE + SERVICE_REPAIR_PC_NOTEBOOKS_TEXT
    keyboard = [
        [InlineKeyboardButton("Заказать бесплатную диагностику 🛠️", callback_data='order_diagnostic_menu')],
        [InlineKeyboardButton("Вернуться в Услуги 🔙", callback_data='our_services_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def service_it_support_orgs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = SERVICE_IT_SUPPORT_TITLE + SERVICE_IT_SUPPORT_TEXT
    keyboard = [
        [InlineKeyboardButton("Заказать бесплатную диагностику 🛠️", callback_data='order_diagnostic_menu')],
        [InlineKeyboardButton("Вернуться в Услуги 🔙", callback_data='our_services_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def service_video_surveillance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = SERVICE_VIDEO_SURVEILLANCE_TITLE + SERVICE_VIDEO_SURVEILLANCE_TEXT
    keyboard = [
        [InlineKeyboardButton("Заказать бесплатную диагностику 🛠️", callback_data='order_diagnostic_menu')],
        [InlineKeyboardButton("Вернуться в Услуги 🔙", callback_data='our_services_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# ==============================================================================
# АДМИНИСТРАТИВНЫЕ ФУНКЦИИ И ФУНКЦИИ ДЛЯ МЕНЕДЖЕРОВ
# ==============================================================================

async def admin_redeem_points_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Начинает процесс списания баллов менеджером.
    """
    if not is_manager(update.effective_user.id):
        await update.message.reply_text(ADMIN_NO_ACCESS)
        return

    await update.message.reply_text(
        ADMIN_ENTER_CODE_PROMPT,
        reply_markup=ForceReply(selective=True)
    )
    context.user_data['state'] = 'awaiting_redeem_code'

async def handle_manager_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ввод менеджера в процессе списания баллов.
    """
    manager_id = update.effective_user.id
    manager_name = update.effective_user.first_name if update.effective_user.first_name else "Менеджер"

    if context.user_data.get('state') == 'awaiting_redeem_code':
        redeem_code = update.message.text
        codes_data = load_codes_data()
        code_info = codes_data.get(redeem_code)

        if not code_info:
            await update.message.reply_text(ADMIN_INVALID_CODE)
            context.user_data['state'] = None
            return

        if code_info["status"] != "pending" or (datetime.now() - datetime.fromisoformat(code_info["generated_at"])).total_seconds() > 600:
            await update.message.reply_text(ADMIN_CODE_EXPIRED)
            context.user_data['state'] = None
            return

        context.user_data['redeem_code_in_progress'] = redeem_code
        await update.message.reply_text(
            ADMIN_ENTER_ORDER_SUM,
            reply_markup=ForceReply(selective=True)
        )
        context.user_data['state'] = 'awaiting_order_sum'
        return

    elif context.user_data.get('state') == 'awaiting_order_sum':
        order_sum_str = update.message.text
        try:
            order_sum = float(order_sum_str)
            if order_sum <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(ADMIN_INVALID_SUM)
            return

        redeem_code = context.user_data.get('redeem_code_in_progress')
        codes_data = load_codes_data()
        code_info = codes_data.get(redeem_code)

        if not code_info or code_info["status"] != "pending":
            await update.message.reply_text(ADMIN_CLIENT_ERROR)
            context.user_data['state'] = None
            context.user_data['redeem_code_in_progress'] = None
            return

        client_user_id = code_info["user_id"]
        p_id = str(client_user_id)
        if not p_id.startswith("TG_") and not p_id.startswith("MAX_"):
            p_id = f"TG_{client_user_id}"
            
        client_user_data = get_user(p_id)
        if not client_user_data:
            await update.message.reply_text(ADMIN_CLIENT_NOT_FOUND)
            context.user_data['state'] = None
            context.user_data['redeem_code_in_progress'] = None
            return

        total_available_points = client_user_data["bonus_points_current"] + client_user_data["regular_points"]
        max_redeem_from_order = order_sum * 0.30
        points_to_redeem = min(total_available_points, max_redeem_from_order)
        final_price = order_sum - points_to_redeem

        code_info["order_sum"] = order_sum
        code_info["amount_to_redeem"] = points_to_redeem
        code_info["final_price"] = final_price
        code_info["manager_id"] = manager_id
        save_codes_data(codes_data)

        context.user_data['current_redemption'] = {
            "code": redeem_code,
            "client_id": client_user_id,
            "order_sum": order_sum,
            "points_to_redeem": points_to_redeem,
            "final_price": final_price,
            "manager_id": manager_id,
            "manager_name": manager_name
        }

        text = ADMIN_PREVIEW_CALCULATION.format(
            client_name=client_user_data.get('first_name', 'Неизвестно'),
            client_id=client_user_id,
            order_sum=order_sum,
            available_points=total_available_points,
            max_redeem=max_redeem_from_order,
            points_to_redeem=points_to_redeem,
            final_price=final_price
        )
        keyboard = [
            [InlineKeyboardButton("Отправить подтверждение клиенту", callback_data='send_client_confirm')],
            [InlineKeyboardButton("Отменить операцию", callback_data='cancel_redeem_admin')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        context.user_data['state'] = 'awaiting_manager_confirm'
        return

    else:
        await update.message.reply_text(ADMIN_UNKNOWN_STATE)

async def send_client_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет клиенту запрос на подтверждение списания баллов.
    """
    query = update.callback_query
    await query.answer()

    redemption_info = context.user_data.get('current_redemption')
    if not redemption_info:
        await query.edit_message_text(ADMIN_SEND_ERROR)
        return

    client_user_id = redemption_info["client_id"]
    order_sum = redemption_info["order_sum"]
    points_to_redeem = redemption_info["points_to_redeem"]
    final_price = redemption_info["final_price"]
    manager_name = redemption_info.get("manager_name", "Менеджер")

    text = CLIENT_CONFIRM_REQUEST.format(
        manager_name=manager_name,
        order_sum=order_sum,
        points_to_redeem=points_to_redeem,
        final_price=final_price
    )
    keyboard = [
        [InlineKeyboardButton("Подтвердить", callback_data=f'confirm_redeem_{redemption_info["code"]}')],
        [InlineKeyboardButton("Отклонить", callback_data=f'cancel_redeem_client_{redemption_info["code"]}')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=client_user_id, text=text, reply_markup=reply_markup, parse_mode='HTML')

    await query.edit_message_text(ADMIN_SENT_TO_CLIENT, parse_mode='HTML')
    context.user_data['state'] = None
    context.user_data['redeem_code_in_progress'] = None
    context.user_data['current_redemption'] = None

async def confirm_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Подтверждает списание баллов клиентом.
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    _, _, redeem_code = query.data.split('_')

    codes_data = load_codes_data()
    code_info = codes_data.get(redeem_code)

    if not code_info or code_info["user_id"] != user_id or code_info["status"] != "pending":
        await query.edit_message_text(CLIENT_REDEEM_ERROR)
        return

    code_info["status"] = "used"
    save_codes_data(codes_data)

    p_id = f"TG_{user_id}"
    client_user_data = get_user(p_id)
    points_to_redeem = code_info["amount_to_redeem"]
    final_price = code_info["final_price"]
    order_sum = code_info["order_sum"]
    manager_id = code_info["manager_id"]

    if client_user_data["bonus_points_current"] >= points_to_redeem:
        client_user_data["bonus_points_current"] -= points_to_redeem
    else:
        remaining_to_redeem = points_to_redeem - client_user_data["bonus_points_current"]
        client_user_data["bonus_points_current"] = 0
        client_user_data["regular_points"] -= remaining_to_redeem

    if points_to_redeem > 0:
        client_user_data["bonus_reminders_active"] = False
    
    context.job_queue.run_once(review_handlers.job_review_request, when=86400, user_id=user_id, name=f"review_req_{user_id}")
    
    update_user(p_id, client_user_data)

    text_client = CLIENT_REDEEM_SUCCESS.format(
        bonus_points=client_user_data['bonus_points_current'],
        regular_points=client_user_data['regular_points'],
        final_price=final_price
    )
    await query.edit_message_text(text_client, parse_mode='HTML')

    if manager_id:
        text_manager = MANAGER_REDEEM_CONFIRMED.format(
            client_name=client_user_data.get('first_name', 'Неизвестно'),
            client_id=user_id,
            code=redeem_code,
            points_to_redeem=points_to_redeem,
            final_price=final_price,
            order_sum=order_sum
        )
        await context.bot.send_message(chat_id=manager_id, text=text_manager, parse_mode='HTML')

    admin_message = ADMIN_REDEEM_COMPLETED.format(
        client_name=client_user_data.get('first_name', 'Неизвестно'),
        client_id=user_id,
        manager_name=code_info.get('manager_name', 'Неизвестно'),
        manager_id=manager_id,
        order_sum=order_sum,
        points_to_redeem=points_to_redeem,
        final_price=final_price,
        bonus_points=client_user_data['bonus_points_current'],
        regular_points=client_user_data['regular_points']
    )
    await context.bot.send_message(chat_id=ADMIN_NOTIFICATION_CHAT_ID, text=admin_message, parse_mode='HTML')

async def cancel_redeem_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отменяет операцию списания баллов менеджером.
    """
    query = update.callback_query
    await query.answer()

    redemption_info = context.user_data.get('current_redemption')
    if redemption_info:
        redeem_code = redemption_info["code"]
        codes_data = load_codes_data()
        if redeem_code in codes_data:
            codes_data[redeem_code]["status"] = "canceled_by_manager"
            save_codes_data(codes_data)

        context.user_data['state'] = None
        context.user_data['redeem_code_in_progress'] = None
        context.user_data['current_redemption'] = None

        await query.edit_message_text(ADMIN_CANCELED_BY_MANAGER, parse_mode='HTML')

        admin_message = ADMIN_NOTIFY_CANCELED_BY_MANAGER.format(
            manager_name=query.from_user.first_name,
            manager_id=query.from_user.id,
            code=redeem_code
        )
        await context.bot.send_message(chat_id=ADMIN_NOTIFICATION_CHAT_ID, text=admin_message, parse_mode='HTML')

async def cancel_redeem_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass

async def handle_review_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает решение менеджера по проверке отзыва (Одобрить/Отклонить).
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    action = parts[2]
    target_user_id = parts[3]
    
    p_id = f"TG_{target_user_id}"
    user_data = get_user(p_id)
    
    if not user_data:
        await query.edit_message_caption(caption=query.message.caption + "\n\n❌ Ошибка: Пользователь не найден в БД.")
        return

    if action == 'approve':
        platform = parts[4]
        user_data['bonus_points_current'] = user_data.get('bonus_points_current', 0) + 500
        
        if platform == 'yandex':
            user_data['yandex_review_status'] = 'verified'
        elif platform == '2gis':
            user_data['twogis_review_status'] = 'verified'
            
        update_user(p_id, user_data)
        
        try:
            success_text = (
                f"🎉 <b>Поздравляем!</b> Ваш отзыв на {platform.upper()} подтвержден.\n"
                f"Вам начислено <b>500 баллов</b>. Спасибо за поддержку! 🙌"
            )
            await context.bot.send_message(chat_id=target_user_id, text=success_text, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id}: {e}")

        await query.edit_message_caption(
            caption=query.message.caption + f"\n\n✅ <b>ОДОБРЕНО (+500 баллов)</b>\nПроверил: {query.from_user.first_name}",
            reply_markup=None,
            parse_mode='HTML'
        )
        
    elif action == 'reject':
        try:
            reject_text = (
                "❌ К сожалению, мы не смогли подтвердить ваш отзыв.\n"
                "Убедитесь, что отзыв опубликован и виден всем пользователям, и попробуйте отправить пруф снова через меню бонусов."
            )
            await context.bot.send_message(chat_id=target_user_id, text=reject_text, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id}: {e}")

        await query.edit_message_caption(
            caption=query.message.caption + f"\n\n❌ <b>ОТКЛОНЕНО</b>\nПроверил: {query.from_user.first_name}",
            reply_markup=None,
            parse_mode='HTML'
        )
