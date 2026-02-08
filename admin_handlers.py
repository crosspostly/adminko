from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply
from telegram.ext import ContextTypes
import logging

from .data_manager import get_user, update_user, load_codes_data, save_codes_data
from .config import ADMIN_NOTIFICATION_CHAT_ID, MANAGER_IDS
from .utils import generate_redeem_code, is_manager, format_date_for_ru

logger = logging.getLogger(__name__)

# ==============================================================================
# АДМИНИСТРАТИВНЫЕ ФУНКЦИИ И ФУНКЦИИ ДЛЯ МЕНЕДЖЕРОВ
# Эти функции предназначены для управления баллами клиентов и работы с заявками.
# Доступ к ним должен быть ограничен только для пользователей с правами менеджера.
# ==============================================================================

async def admin_redeem_points_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Начинает процесс списания баллов менеджером.
    Проверяет, является ли пользователь менеджером.
    Запрашивает 6-значный код клиента для списания баллов.
    """
    if not is_manager(update.effective_user.id):  # Проверка прав менеджера
        await update.message.reply_text("У вас нет прав администратора для этой команды.")
        return

    await update.message.reply_text(
        "Введите 6-значный код клиента для списания баллов:",
        reply_markup=ForceReply(selective=True)
    )
    # Устанавливаем состояние 'awaiting_redeem_code' для пользователя менеджера,
    # чтобы следующий текстовый ввод был обработан функцией handle_manager_input
    context.user_data['state'] = 'awaiting_redeem_code'

async def handle_manager_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ввод менеджера в процессе списания баллов:
    - Принимает 6-значный код клиента.
    - Принимает сумму заказа.
    Проводит расчет списания баллов и предлагает отправить запрос клиенту.
    """
    manager_id = update.effective_user.id
    manager_name = update.effective_user.first_name if update.effective_user.first_name else "Менеджер"

    # Шаг 1: Ожидание 6-значного кода клиента
    if context.user_data.get('state') == 'awaiting_redeem_code':
        redeem_code = update.message.text
        codes_data = load_codes_data()
        code_info = codes_data.get(redeem_code)

        # Проверка кода
        if not code_info:
            await update.message.reply_text("Неверный код или срок действия истек. Попробуйте еще раз.")
            context.user_data['state'] = None # Сброс состояния
            return

        # Проверка статуса и срока действия кода (10 минут)
        if code_info["status"] != "pending" or (datetime.now() - datetime.fromisoformat(code_info["generated_at"])).total_seconds() > 600:
            await update.message.reply_text("Код недействителен или срок действия истек. Попробуйте еще раз.")
            context.user_data['state'] = None # Сброс состояния
            return

        # Сохраняем код для следующего шага и переходим к запросу суммы заказа
        context.user_data['redeem_code_in_progress'] = redeem_code
        await update.message.reply_text(
            "Введите сумму заказа (например, 1500.50):",
            reply_markup=ForceReply(selective=True)
        )
        context.user_data['state'] = 'awaiting_order_sum' # Переход к следующему состоянию
        return

    # Шаг 2: Ожидание суммы заказа
    elif context.user_data.get('state') == 'awaiting_order_sum':
        order_sum_str = update.message.text
        try:
            order_sum = float(order_sum_str)
            if order_sum <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Неверный формат суммы. Введите числовое значение.")
            return

        redeem_code = context.user_data.get('redeem_code_in_progress')
        codes_data = load_codes_data()
        code_info = codes_data.get(redeem_code)

        # Повторная проверка кода и статуса
        if not code_info or code_info["status"] != "pending":
            await update.message.reply_text("Ошибка с кодом. Попробуйте заново начать с /admin_redeem_points.")
            context.user_data['state'] = None
            context.user_data['redeem_code_in_progress'] = None
            return

        client_user_id = code_info["user_id"]
        client_user_data = get_user(client_user_id)
        if not client_user_data:
            await update.message.reply_text("Клиент не найден. Возможно, пользователь удален.")
            context.user_data['state'] = None
            context.user_data['redeem_code_in_progress'] = None
            return

        # Расчет списания баллов (макс. 30% от суммы заказа)
        total_available_points = client_user_data["bonus_points_current"] + client_user_data["regular_points"]
        max_redeem_from_order = order_sum * 0.30
        points_to_redeem = min(total_available_points, max_redeem_from_order)
        final_price = order_sum - points_to_redeem

        # Обновляем информацию о коде
        code_info["order_sum"] = order_sum
        code_info["amount_to_redeem"] = points_to_redeem
        code_info["final_price"] = final_price
        code_info["manager_id"] = manager_id
        save_codes_data(codes_data)

        # Сохраняем информацию о текущей операции для подтверждения
        context.user_data['current_redemption'] = {
            "code": redeem_code,
            "client_id": client_user_id,
            "order_sum": order_sum,
            "points_to_redeem": points_to_redeem,
            "final_price": final_price,
            "manager_id": manager_id,
            "manager_name": manager_name
        }

        # Предварительный расчет для менеджера
        text = (
            f"Предварительный расчет:
" +
            f"Клиент: {client_user_data.get('first_name', 'Неизвестно')} (`{client_user_id}`)
" +
            f"Сумма заказа: **{order_sum:.2f}** руб.
" +
            f"Доступно баллов: {total_available_points:.2f} руб.
" +
            f"Макс. к списанию (30% от заказа): {max_redeem_from_order:.2f} руб.
" +
            f"**Будет списано: {points_to_redeem:.2f} руб.**
" +
            f"**Итого к оплате: {final_price:.2f} руб.**

" +
            "Отправить запрос на подтверждение клиенту?"
        )
        keyboard = [
            [InlineKeyboardButton("Отправить подтверждение клиенту", callback_data='send_client_confirm')],
            [InlineKeyboardButton("Отменить операцию", callback_data='cancel_redeem_admin')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        context.user_data['state'] = 'awaiting_manager_confirm' # Переход к состоянию ожидания подтверждения менеджера
        return

    else:
        await update.message.reply_text("Неизвестное состояние. Пожалуйста, начните заново.")

async def send_client_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет клиенту запрос на подтверждение списания баллов.
    Вызывается после того, как менеджер ввел код и сумму заказа.
    """
    query = update.callback_query
    await query.answer()

    redemption_info = context.user_data.get('current_redemption')
    if not redemption_info:
        await query.edit_message_text("Ошибка: информация о списании не найдена. Попробуйте заново.")
        return

    client_user_id = redemption_info["client_id"]
    order_sum = redemption_info["order_sum"]
    points_to_redeem = redemption_info["points_to_redeem"]
    final_price = redemption_info["final_price"]
    manager_name = redemption_info.get("manager_name", "Менеджер")

    text = (
        f"Подтвердите списание баллов:

" +
        f"Ваш менеджер **{manager_name}** оформил услугу на сумму **{order_sum:.2f} руб.**
" +
        f"Будет списано: **{points_to_redeem:.2f} руб.**
" +
        f"**Итого к оплате наличными менеджеру: {final_price:.2f} руб.**

" +
        "Вы подтверждаете?"
    )
    keyboard = [
        [InlineKeyboardButton("Подтвердить", callback_data=f'confirm_redeem_{redemption_info["code"]}')],
        [InlineKeyboardButton("Отклонить", callback_data=f'cancel_redeem_client_{redemption_info["code"]}')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение клиенту
    await context.bot.send_message(chat_id=client_user_id, text=text, reply_markup=reply_markup, parse_mode='Markdown')

    await query.edit_message_text("Запрос на подтверждение отправлен клиенту.", parse_mode='Markdown')
    # Сброс состояний менеджера после отправки запроса
    context.user_data['state'] = None
    context.user_data['redeem_code_in_progress'] = None
    context.user_data['current_redemption'] = None

async def confirm_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Подтверждает списание баллов клиентом.
    Обновляет данные клиента и кода, уведомляет менеджера и администратора.
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    _, _, redeem_code = query.data.split('_')

    codes_data = load_codes_data()
    code_info = codes_data.get(redeem_code)

    # Проверка валидности кода и соответствия пользователя
    if not code_info or code_info["user_id"] != user_id or code_info["status"] != "pending":
        await query.edit_message_text("Ошибка: код недействителен или уже использован.")
        return

    # Обновляем статус кода на "использован"
    code_info["status"] = "used"
    save_codes_data(codes_data)

    client_user_data = get_user(user_id)
    points_to_redeem = code_info["amount_to_redeem"]
    final_price = code_info["final_price"]
    order_sum = code_info["order_sum"]
    manager_id = code_info["manager_id"]

    # Списание баллов с баланса клиента
    if client_user_data["bonus_points_current"] >= points_to_redeem:
        client_user_data["bonus_points_current"] -= points_to_redeem
    else:
        remaining_to_redeem = points_to_redeem - client_user_data["bonus_points_current"]
        client_user_data["bonus_points_current"] = 0
        client_user_data["regular_points"] -= remaining_to_redeem  # Списываем из регулярных, если бонусов не хватило

    # Отключаем напоминания о бонусе, если он использован
    if points_to_redeem > 0:
        client_user_data["bonus_reminders_active"] = False
    update_user(user_id, client_user_data)

    # Уведомление клиенту об успешном списании
    text_client = (
        "✅ Баллы успешно списаны!

" +
        f"Ваш новый баланс: **{client_user_data['bonus_points_current']} руб.** (бонусы) / **{client_user_data['regular_points']} руб.** (обычные).
" +
        f"К оплате менеджеру: **{final_price:.2f} руб.**

" +
        "Спасибо за выбор наших услуг!"
    )
    await query.edit_message_text(text_client, parse_mode='Markdown')

    # Уведомление менеджеру (если был менеджер)
    if manager_id:
        text_manager = (
            f"✅ Списание баллов для клиента {client_user_data.get('first_name', 'Неизвестно')} (`{user_id}`) подтверждено.
" +
            f"Код: `{redeem_code}`.
" +
            f"Списано: **{points_to_redeem:.2f} руб.**
" +
            f"Итого к оплате: **{final_price:.2f} руб.**
" +
            f"Сумма заказа: **{order_sum:.2f} руб.**
"
        )
        await context.bot.send_message(chat_id=manager_id, text=text_manager, parse_mode='Markdown')
        
    # Уведомление администратору о завершении списания
    admin_message = (
        f"✅ **Списание баллов завершено!**
" +
        f"Клиент: {client_user_data.get('first_name', 'Неизвестно')} (`{user_id}`)
" +
        f"Менеджер: {code_info.get('manager_name', 'Неизвестно')} (`{manager_id}`)
" +
        f"Сумма заказа: **{order_sum:.2f} руб.**
" +
        f"Списано баллов: **{points_to_redeem:.2f} руб.**
"
        f"Итого к оплате: **{final_price:.2f} руб.**
"
        f"Новый баланс клиента: {client_user_data['bonus_points_current']} (бонусы) / {client_user_data['regular_points']} (обычные).
"
    )
    await context.bot.send_message(chat_id=ADMIN_NOTIFICATION_CHAT_ID, text=admin_message, parse_mode='Markdown')

async def cancel_redeem_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отменяет операцию списания баллов менеджером.
    Уведомляет администратора об отмене.
    """
    query = update.callback_query
    await query.answer()

    redemption_info = context.user_data.get('current_redemption')
    if redemption_info:
        redeem_code = redemption_info["code"]
        codes_data = load_codes_data()
        if redeem_code in codes_data:
            codes_data[redeem_code]["status"] = "canceled_by_manager" # Обновляем статус кода
            save_codes_data(codes_data)

        # Сброс состояний менеджера
        context.user_data['state'] = None
        context.user_data['redeem_code_in_progress'] = None
        context.user_data['current_redemption'] = None

        await query.edit_message_text("❌ Операция списания баллов отменена менеджером.", parse_mode='Markdown')
        
        # Уведомление администратору об отмене
        admin_message = (
            f"❌ **Операция списания баллов отменена менеджером!**
" +
            f"Менеджер: {query.from_user.first_name} (`{query.from_user.id}`)
" +
            f"Код клиента: `{redeem_code}`
"
        )
        await context.bot.send_message(chat_id=ADMIN_NOTIFICATION_CHAT_ID, text=admin_message, parse_mode='Markdown')

async def cancel_redeem_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отменяет операцию списания баллов клиентом.
    Обновляет статус кода, уведомляет менеджера и администратора.
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    _, _, _, redeem_code = query.data.split('_')

    codes_data = load_codes_data()
    code_info = codes_data.get(redeem_code)

    if code_info and code_info["user_id"] == user_id and code_info["status"] == "pending":
        code_info["status"] = "canceled_by_client" # Обновляем статус кода
        save_codes_data(codes_data)

        # Уведомление менеджеру, если он был инициатором операции
        if code_info["manager_id"]:
            await context.bot.send_message(
                chat_id=code_info["manager_id"],
                text=f"❌ Клиент {query.from_user.first_name} (`{user_id}`) отклонил списание баллов по коду `{redeem_code}`.
",
                parse_mode='Markdown'
            )
        await query.edit_message_text("❌ Списание баллов отменено по вашему запросу.", parse_mode='Markdown')
        
        # Уведомление администратору об отмене клиентом
        admin_message = (
            f"❌ **Клиент отклонил списание баллов!**
"
            f"Клиент: {query.from_user.first_name} (`{user_id}`)
"
            f"Менеджер: {code_info.get('manager_name', 'Неизвестно')} (`{code_info.get('manager_id', 'Неизвестно')}`)
"
            f"Код: `{redeem_code}`
"
        )
        await context.bot.send_message(chat_id=ADMIN_NOTIFICATION_CHAT_ID, text=admin_message, parse_mode='Markdown')
    else:
        await query.edit_message_text("Ошибка: операция списания не найдена или уже завершена.")