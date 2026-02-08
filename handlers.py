from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply
from telegram.ext import ContextTypes
import logging

from .data_manager import get_user, update_user, load_codes_data, save_codes_data
from .config import TEST_QUESTIONS, ADMIN_NOTIFICATION_CHAT_ID
from .utils import generate_redeem_code, format_date_for_ru

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
        text = (
            "Привет! 👋 Добро пожаловать в мир заботы о вашем ПК! Я — ваш надежный помощник, готовый раскрыть все секреты здоровья вашего компьютера. "
            "Пройдите наш увлекательный **Экспресс-тест из 8 вопросов**, чтобы моментально узнать о потенциальных проблемах. "
            "Это займет всего пару минут, а результат вас приятно удивит!

" +
            "А еще... за прохождение теста вас ждет ценный подарок! 🎁"
        )
    elif not user_data["bonus_given_flag"]:
        text = (
            "С возвращением! 👋 Рад снова видеть вас! Готовы узнать еще больше о вашем компьютере? "
            "Наш **Экспресс-тест (8 вопросов)** поможет быстро выявить скрытые неполадки. "
            "Всего пара минут — и полная картина у вас в руках!

" +
            "Не забудьте: за прохождение теста вас ждет классный подарок! 🎁"
        )
    else:
        text = (
            "Привет-привет! 👋 Снова здесь? Отлично! Ваш персональный помощник по здоровью компьютера к вашим услугам. "
            "Если хотите, можете пройти наш **Экспресс-тест (8 вопросов)** еще раз, чтобы убедиться, что с вашим ПК всё в порядке. "
            "Это быстро и полезно! 😉"
        )

    keyboard = [
        [InlineKeyboardButton("🚀 Начать Экспресс-тест", callback_data='start_test')],
        [InlineKeyboardButton("💼 Наши услуги", callback_data='our_services_menu')],
        [InlineKeyboardButton("👤 Личный кабинет", callback_data='personal_account_menu')],
        [InlineKeyboardButton("ℹ️ Контакты и о нас", callback_data='contact_us_menu')], # Объединенная кнопка
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

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
                f"

✨ Напоминаем: у вас есть **{user_data['bonus_points_current']} бонусных рублей** до "
                f"**{format_date_for_ru(expiry_date_str)}**!"
            )

    text = (
        "Мы предлагаем широкий спектр услуг для частных клиентов и бизнеса: 💼

"
        "Выберите интересующую категорию, чтобы узнать подробнее: 👇"
        f"{bonus_reminder_text}"
    )
    keyboard = [
        [InlineKeyboardButton("Ремонт ПК/Ноутбуков 💻", callback_data='service_repair_pc_notebooks')],
        [InlineKeyboardButton("IT-обслуживание 🏢", callback_data='service_it_support_orgs')],
        [InlineKeyboardButton("Монтаж видеонаблюдения 📹", callback_data='service_video_surveillance')],
        [InlineKeyboardButton("Заказать бесплатную диагностику 🛠️", callback_data='order_diagnostic_menu')],
        [InlineKeyboardButton("Связаться с нами 📞", callback_data='contact_us_menu')],
        [InlineKeyboardButton("Вернуться в главное меню 🏡", callback_data='start_menu_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message_editor(text, reply_markup=reply_markup, parse_mode='Markdown')

async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message_editor = query.edit_message_text
    else:
        message_editor = update.message.reply_text

    text = (
        "📞 **Контакты и О нас** ℹ️

"
        "Мы всегда рады помочь вам с любыми вопросами, связанными с ремонтом и обслуживанием компьютерной техники, "
        "IT-поддержкой и установкой систем видеонаблюдения.

"
        "**Наши контакты:**
"
        "🔹 Телефон: `+7 (3842) 76-76-76`
"
        "🔹 WhatsApp: [Написать в WhatsApp](https://wa.me/73842767676)
"
        "🔹 Email: `info@example.com` (замените на реальный)

"
        "Мы работаем, чтобы ваша техника работала без сбоев, а бизнес процветал благодаря надежной IT-инфраструктуре!
"
    )
    keyboard = [
        [InlineKeyboardButton("↩️ Главное меню", callback_data='start_menu_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message_editor(text, reply_markup=reply_markup, parse_mode='Markdown', disable_web_page_preview=True)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user(user_id)
    if user_data is None:
        await query.edit_message_text("Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    current_question_index = user_data["test_progress"]

    if current_question_index >= len(TEST_QUESTIONS):
        await show_test_results(update, context)
        return

    question_text = TEST_QUESTIONS[current_question_index]["text"]
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data=f'test_answer_{current_question_index}_1'),
            InlineKeyboardButton("Нет", callback_data=f'test_answer_{current_question_index}_0'),
            InlineKeyboardButton("Не знаю", callback_data=f'test_answer_{current_question_index}_0')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Вопрос {current_question_index + 1}/8: {question_text}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user(user_id)
    if user_data is None:
        await query.edit_message_text("Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    _, _, question_index_str, answer_str = query.data.split('_')
    question_index = int(question_index_str)
    answer = int(answer_str)

    if question_index != user_data["test_progress"]:
        # Пользователь ответил на старый вопрос, игнорируем
        return

    user_data["test_answers"][question_index] = answer
    user_data["test_progress"] += 1
    update_user(user_id, user_data)

    if user_data["test_progress"] < len(TEST_QUESTIONS):
        await ask_question(update, context)  # Следующий вопрос
    else:
        await show_test_results(update, context)  # Результаты теста

async def show_test_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user(user_id)
    if user_data is None:
        await query.edit_message_text("Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    positive_answers = sum(user_data["test_answers"])
    result_text = f"По нашим данным, у вашего компьютера есть **{positive_answers}** потенциальных проблем. "

    if 0 <= positive_answers <= 1:
        result_text += "Кажется, ваш компьютер в хорошем состоянии! Но профилактика никогда не помешает."
    elif 2 <= positive_answers <= 4:
        result_text += "Есть над чем поработать. Рекомендуем обратить внимание на эти моменты."
    elif 5 <= positive_answers <= 8:
        result_text += "Вашему компьютеру определенно нужна помощь! Не откладывайте диагностику."

    bonus_info_text = ""
    if not user_data["bonus_given_flag"]:
        user_data["bonus_points_current"] = user_data["bonus_points_initial"]
        user_data["bonus_expiry_date"] = (datetime.now() + timedelta(weeks=2)).isoformat()
        user_data["bonus_given_flag"] = True
        user_data["bonus_reminders_active"] = True
        update_user(user_id, user_data)

        bonus_info_text = (
            f"

**Ваш приятный подарок!** За прохождение теста мы **зачислили 1000 рублей** на ваш счет! " +
            "Эти средства вы можете использовать для оплаты любых наших услуг. " +
            f"**Важно:** Бонус действует **до {format_date_for_ru(user_data['bonus_expiry_date'])}**. Успейте воспользоваться!"
        )
    elif user_data["bonus_given_flag"] and user_data["bonus_points_current"] > 0 and datetime.fromisoformat(user_data["bonus_expiry_date"]) > datetime.now():
        bonus_info_text = (
            f"

Напоминаем, что у вас есть **{user_data['bonus_points_current']} рублей** на счету, " +
            f"которые вы можете использовать для оплаты диагностики или других услуг до " +
            f"**{format_date_for_ru(user_data['bonus_expiry_date'])}**."
        )

    text = f"Отлично! Вы завершили Экспресс-тест. {result_text}{bonus_info_text}"
    keyboard = [
        [InlineKeyboardButton("Заказать бесплатную диагностику", callback_data='order_diagnostic_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    # Сброс прогресса теста
    user_data["test_progress"] = 0
    user_data["test_answers"] = [0]*8
    update_user(user_id, user_data)

async def order_diagnostic_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user(user_id)
    
    first_name = query.from_user.first_name if query.from_user.first_name else "пользователь"

    bonus_reminder_text = ""
    if user_data and user_data["bonus_given_flag"] and user_data["bonus_points_current"] > 0 and datetime.fromisoformat(user_data["bonus_expiry_date"]) > datetime.now():
        bonus_reminder_text = (
            f"

Напоминаем, что у вас есть **{user_data['bonus_points_current']} рублей** на счету, " +
            f"которые вы можете использовать для оплаты диагностики или других услуг до " +
            f"**{format_date_for_ru(user_data['bonus_expiry_date'])}**."
        )

    text = (
        f"Привет, {first_name}! 👋 Чтобы получить точную информацию о состоянии вашего компьютера или заказать любую другую услугу, " +
        "выберите удобный способ связи:

" +
        "**Связаться с нами** или **позвонить сейчас**?" +
        f"{bonus_reminder_text}"
    )
    keyboard = [
        [InlineKeyboardButton("Связаться с нами 📞", callback_data='request_callback')],
        [InlineKeyboardButton("Позвонить нам ☎️", url='tel:+73842767676')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def request_phone_number_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    first_name = query.from_user.first_name if query.from_user.first_name else "пользователь"

    text = (
        f"Привет, {first_name}! 👋 Чтобы мы могли с вами связаться, " +
        "пожалуйста, поделитесь своим номером телефона. " +
        "Вы можете нажать кнопку ниже или ввести номер вручную в формате +79XXXXXXXXX."
    )
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
        await update.message.reply_text("Неверный формат номера. Пожалуйста, введите номер в формате +79XXXXXXXXX.", reply_markup=ReplyKeyboardRemove())
        return

    user_data = get_user(user_id) # Assume get_user is available in bot.py
    if user_data:
        user_data["phone_number"] = phone_number
        update_user(user_id, user_data) # Assume update_user is available in bot.py
        
        bonus_reminder_text = ""
        if user_data and user_data["bonus_given_flag"] and user_data["bonus_points_current"] > 0 and datetime.fromisoformat(user_data["bonus_expiry_date"]) > datetime.now():
            bonus_reminder_text = (
                f"Напоминаем, что у вас есть **{user_data['bonus_points_current']} рублей** на счету, " +
                f"которые вы можете использовать для оплаты диагностики или других услуг до " +
                f"**{format_date_for_ru(user_data['bonus_expiry_date'])}**."
            )

        text = (
            f"Спасибо, {first_name}! Мы получили ваш номер телефона ({phone_number}) и скоро свяжемся с вами для уточнения деталей!
" +
            f"{bonus_reminder_text}"
        )
        await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
        context.user_data['state'] = None
        
        admin_message = (
            f"🔔 **Новая заявка на обратный звонок!**
" +
            f"Имя: {first_name}
" +
            f"ID: `{user_id}`
" +
            f"Username: @{username}
" +
            f"Телефон: `{phone_number}`
"
        )
        await context.bot.send_message(chat_id=ADMIN_NOTIFICATION_CHAT_ID, text=admin_message, parse_mode='Markdown')
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
                f"Напоминаем, что у вас есть **{user_data['bonus_points_current']} рублей** на счету, " +
                f"которые вы можете использовать для оплаты диагностики или других услуг до " +
                f"**{format_date_for_ru(user_data['bonus_expiry_date'])}**."
            )

        text = (
            f"Спасибо, {first_name}! Мы получили ваш номер телефона ({phone_number}) и скоро свяжемся с вами для уточнения деталей!
" +
            f"{bonus_reminder_text}"
        )
        await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
        context.user_data['state'] = None # Сбрасываем состояние

        admin_message = (
            f"🔔 **Новая заявка на обратный звонок!**
" +
            f"Имя: {first_name}
" +
            f"ID: `{user_id}`
" +
            f"Username: @{username}
" +
            f"Телефон: `{phone_number}`
"
        )
        await context.bot.send_message(chat_id=ADMIN_NOTIFICATION_CHAT_ID, text=admin_message, parse_mode='Markdown')
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
            await update.callback_query.edit_message_text("Пожалуйста, начните с команды /start.")
        else: # Иначе через reply_text
            await update.message.reply_text("Пожалуйста, начните с команды /start.")
        return

    bonus_info = ""
    if user_data.get("bonus_points_current", 0) > 0 and user_data.get("bonus_expiry_date") and datetime.fromisoformat(user_data["bonus_expiry_date"]) > datetime.now():
        bonus_info = (
            f"   • Начислено бонусов: **{user_data['bonus_points_current']} руб.** " +
            f"(действуют до: **{format_date_for_ru(user_data['bonus_expiry_date'])}**)
"
        )

    regular_info = ""
    # if user_data["regular_points"] > 0:
    #     regular_info = f"   • Накоплено баллов: **{user_data['regular_points']} руб.**
"
    
    keyboard = []
    
    if not bonus_info and not regular_info:
        balance_text = "У вас пока нет активных баллов."
    else:
        balance_text = (
            f"📊 **Ваши баллы:**
"
            f"{bonus_info}{regular_info}

"
            "Используйте баллы для оплаты до **30%** от суммы заказа!

"
            "Хотите использовать баллы сейчас?"
        )
        keyboard.append([InlineKeyboardButton("Использовать баллы", callback_data='use_points_start')])

    keyboard.append([InlineKeyboardButton("Вернуться в главное меню 🏡", callback_data='start_menu_main')])
    
    final_text = f"Привет, {first_name}! Это ваш Личный кабинет.

{balance_text}"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message_editor(
        final_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def use_points_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user(user_id)

    if not user_data or (user_data["bonus_points_current"] == 0 and user_data["regular_points"] == 0):
        await query.edit_message_text("У вас нет баллов для списания.", parse_mode='Markdown')
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

    text = (
        f"Ваш код для менеджера: **`{code}`**

" +
        "Пожалуйста, покажите этот код менеджеру для применения скидки. " +
        "Код действителен в течение **10 минут**."
    )
    keyboard = [
        [InlineKeyboardButton("Вернуться в Личный кабинет", callback_data='personal_account_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


# НОВЫЕ ФУНКЦИИ ДЛЯ КАТЕГОРИЙ УСЛУГ
async def service_repair_pc_notebooks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = (
        "**Ремонт ПК/Ноутбуков 💻:**

"
        "Мы выполняем полную диагностику, качественный ремонт и профессиональное обслуживание ваших компьютеров и ноутбуков. "
        "Включает: чистку от пыли, замену неисправных компонентов, установку и настройку программного обеспечения, удаление вирусов. "
        "С нами ваша техника будет работать как новая! ✨"
    )
    keyboard = [
        [InlineKeyboardButton("Заказать бесплатную диагностику 🛠️", callback_data='order_diagnostic_menu')],
        [InlineKeyboardButton("Вернуться в Услуги 🔙", callback_data='our_services_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def service_it_support_orgs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = (
        "**IT-обслуживание 🏢:**

"
        "Предлагаем комплексное IT-администрирование для вашего бизнеса. Это включает: "
        "проактивный мониторинг инфраструктуры, регулярное резервное копирование данных, "
        "обеспечение кибербезопасности, а также оперативное решение любых IT-вопросов. "
        "Позвольте нам позаботиться о вашей IT, чтобы вы могли сосредоточиться на бизнесе! 🚀"
    )
    keyboard = [
        [InlineKeyboardButton("Заказать бесплатную диагностику 🛠️", callback_data='order_diagnostic_menu')],
        [InlineKeyboardButton("Вернуться в Услуги 🔙", callback_data='our_services_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def service_video_surveillance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = (
        "**Монтаж систем видеонаблюдения 📹:**

"
        "Разработаем индивидуальный проект системы видеонаблюдения, подберём оптимальное оборудование "
        "и выполним профессиональный монтаж. Обеспечьте безопасность вашего объекта с надёжными системами! 🛡️"
    )
    keyboard = [
        [InlineKeyboardButton("Заказать бесплатную диагностику 🛠️", callback_data='order_diagnostic_menu')],
        [InlineKeyboardButton("Вернуться в Услуги 🔙", callback_data='our_services_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')