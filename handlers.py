from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply
from telegram.ext import ContextTypes
import logging

from data_manager import get_user, update_user, load_codes_data, save_codes_data
from config import ADMIN_NOTIFICATION_CHAT_ID, TEST_HINTS_SHOW_ALERT
from texts import (
    TEST_QUESTIONS, TEST_HINTS,
    START_NEW_USER, START_RETURNING_USER_NO_BONUS, START_RETURNING_USER_WITH_BONUS,
    OUR_SERVICES_TITLE,
    SERVICE_REPAIR_PC_NOTEBOOKS_TITLE, SERVICE_REPAIR_PC_NOTEBOOKS_TEXT,
    SERVICE_IT_SUPPORT_TITLE, SERVICE_IT_SUPPORT_TEXT,
    SERVICE_VIDEO_SURVEILLANCE_TITLE, SERVICE_VIDEO_SURVEILLANCE_TEXT,
    CONTACT_US_TITLE, CONTACT_US_TEXT,
    DIAGNOSTIC_REQUEST_TEXT, REQUEST_PHONE_NUMBER_TEXT, PHONE_RECEIVED_CONFIRMATION,
    INVALID_PHONE_NUMBER_FORMAT, ADMIN_NEW_CALLBACK_REQUEST,
    CABINET_NO_POINTS, CABINET_HAS_POINTS_TITLE, CABINET_POINTS_INFO, CABINET_USE_POINTS_PROMPT, CABINET_NO_USER_ERROR,
    TEST_RESULTS_INTRO, TEST_RESULTS_PROBLEM_COUNT,
    TEST_RESULTS_0_1, TEST_RESULTS_2_4, TEST_RESULTS_5_8,
    TEST_RESULTS_BONUS_NEW, TEST_RESULTS_BONUS_EXISTING,
    USE_POINTS_CODE_GENERATED, USE_POINTS_NO_POINTS,
)
from utils import generate_redeem_code, format_date_for_ru

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if not user_data:
        # Новый пользователь
        registration_date = datetime.now()
        user_data = {
            "user_id": user_id,
            "username": update.effective_user.username,
            "first_name": update.effective_user.first_name,
            "registration_date": registration_date.isoformat(),
            "phone_number": None,
            "bonus_points_initial": 1000,
            "bonus_points_current": 0,  # Начисляем после теста
            "bonus_expiry_date": None,
            "bonus_given_flag": False,
            "bonus_reminders_active": False,
            "regular_points": 0,
            "last_regular_points_accrual_date": None,
            "test_progress": 0,  # 0 - не начат, 1-8 - номер вопроса
            "test_answers": [0]*8  # 0 - нет, 1 - да
        }
        update_user(user_id, user_data)
        text = START_NEW_USER
    elif not user_data["bonus_given_flag"]:
        text = START_RETURNING_USER_NO_BONUS
    else:
        text = START_RETURNING_USER_WITH_BONUS

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
    user_data = get_user(user_id)
    
    if user_data:
        user_data["bonus_given_flag"] = False
        user_data["test_progress"] = 0
        user_data["test_answers"] = [0]*8
        # Мы НЕ обнуляем накопленные баллы (regular_points), 
        # но бонусные (bonus_points_current) сбрасываем, чтобы начислить их заново после теста.
        user_data["bonus_points_current"] = 0
        user_data["bonus_expiry_date"] = None
        
        update_user(user_id, user_data)
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

    user_data = get_user(user_id)
    
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
    user_data = get_user(user_id)
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
    user_data = get_user(user_id)
    if user_data is None:
        await query.edit_message_text("Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    try:
        _, _, question_index_str = query.data.split('_')
        question_index = int(question_index_str)
        user_data["test_progress"] = question_index
        update_user(user_id, user_data)
        await ask_question(update, context, answered=True)
    except Exception as e:
        logger.error(f"Error in next_question: {e}")

async def handle_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    user_data = get_user(user_id)
    if user_data is None:
        await query.answer(show_alert=True, text="Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    try:
        _, _, question_index_str, answer_str = query.data.split('_')
        question_index = int(question_index_str)
        answer = int(answer_str)
        
        # 'Не знаю' (2) обрабатываем как 'Нет' (0)
        if answer == 2:
            answer = 0

        if question_index != user_data["test_progress"]:
            # Пользователь ответил на старый вопрос или на вопрос из другого сеанса
            # Показываем актуальный вопрос, чтобы он не застрял
            await query.answer(show_alert=False, text="Показываю актуальный вопрос...")
            await ask_question(update, context, answered=True)
            return

        user_data["test_answers"][question_index] = answer
        user_data["test_progress"] += 1
        update_user(user_id, user_data)

        # Показываем подсказку после ответа (всплывающее окно)
        hint_text = TEST_HINTS[question_index]

        if user_data["test_progress"] < len(TEST_QUESTIONS):
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
    user_data = get_user(user_id)
    if user_data is None:
        await query.edit_message_text("Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    try:
        positive_answers = sum(user_data["test_answers"])
        result_text = TEST_RESULTS_PROBLEM_COUNT.format(count=positive_answers)

        if 0 <= positive_answers <= 1:
            result_text += TEST_RESULTS_0_1
        elif 2 <= positive_answers <= 4:
            result_text += TEST_RESULTS_2_4
        elif 5 <= positive_answers <= 8:
            result_text += TEST_RESULTS_5_8

        bonus_info_text = ""
        if not user_data["bonus_given_flag"]:
            user_data["bonus_points_current"] = user_data["bonus_points_initial"]
            user_data["bonus_expiry_date"] = (datetime.now() + timedelta(weeks=2)).isoformat()
            user_data["bonus_given_flag"] = True
            user_data["bonus_reminders_active"] = True
            update_user(user_id, user_data)

            bonus_info_text = TEST_RESULTS_BONUS_NEW.format(
                expiry_date=format_date_for_ru(user_data['bonus_expiry_date'])
            )
        elif user_data["bonus_given_flag"] and user_data["bonus_points_current"] > 0:
            # Проверка на наличие даты истечения
            expiry_date_str = user_data.get("bonus_expiry_date")
            if expiry_date_str and datetime.fromisoformat(expiry_date_str) > datetime.now():
                bonus_info_text = TEST_RESULTS_BONUS_EXISTING.format(
                    points=user_data['bonus_points_current'],
                    expiry_date=format_date_for_ru(expiry_date_str)
                )

        text = TEST_RESULTS_INTRO + result_text + bonus_info_text
        keyboard = [
            [InlineKeyboardButton("Заказать бесплатную диагностику 🛠️", callback_data='order_diagnostic_menu')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

        # Сброс прогресса теста в любом случае после показа результатов
        user_data["test_progress"] = 0
        user_data["test_answers"] = [0]*8
        update_user(user_id, user_data)
    except Exception as e:
        logger.error(f"Error in show_test_results: {e}")
        # При ошибке все равно пытаемся сбросить прогресс, чтобы пользователь не застрял
        user_data["test_progress"] = 0
        update_user(user_id, user_data)
        await query.edit_message_text("Произошла ошибка при показе результатов. Пожалуйста, попробуйте снова /start.")

async def order_diagnostic_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user(user_id)
    
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
    phone_number = update.message.text
    first_name = update.effective_user.first_name if update.effective_user.first_name else "Неизвестный"
    username = update.effective_user.username if update.effective_user.username else ""

    # Простая проверка формата номера телефона
    if not (phone_number.startswith('+7') and len(phone_number) == 12 and phone_number[1:].isdigit()):
        await update.message.reply_text(INVALID_PHONE_NUMBER_FORMAT, reply_markup=ReplyKeyboardRemove())
        return

    user_data = get_user(user_id) # Assume get_user is available in bot.py
    if user_data:
        user_data["phone_number"] = phone_number
        update_user(user_id, user_data) # Assume update_user is available in bot.py
        
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
    phone_number = update.message.contact.phone_number
    first_name = update.effective_user.first_name if update.effective_user.first_name else "Неизвестный"
    username = update.effective_user.username if update.effective_user.username else ""

    user_data = get_user(user_id) # Assume get_user is available in bot.py
    if user_data:
        user_data["phone_number"] = phone_number
        update_user(user_id, user_data) # Assume update_user is available in bot.py
        
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

    user_data = get_user(user_id)

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
    user_data = get_user(user_id)

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