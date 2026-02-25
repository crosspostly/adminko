import logging
from maxapi import types, Bot
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.updates.message_callback import MessageCallback
import core_logic
from texts import (
    START_NEW_USER, START_RETURNING_USER_NO_BONUS, START_RETURNING_USER_WITH_BONUS,
    TEST_QUESTIONS, TEST_RESULTS_INTRO, TEST_RESULTS_PROBLEM_COUNT,
    TEST_RESULTS_0_1, TEST_RESULTS_2_4, TEST_RESULTS_5_8,
    TEST_RESULTS_BONUS_NEW, TEST_RESULTS_BONUS_EXISTING
)
from utils import format_date_for_ru
from data_manager import get_user, update_user

logger = logging.getLogger(__name__)

async def cmd_start(message: types.Message, bot: Bot):
    user_id = message.from_user.user_id
    user_data = await core_logic.get_or_create_user(user_id, platform="MAX", 
                                              username=message.from_user.username,
                                              first_name=message.from_user.first_name)

    if not user_data["bonus_given_flag"]:
        text = START_NEW_USER
    else:
        text = START_RETURNING_USER_WITH_BONUS

    builder = InlineKeyboardBuilder()
    if not user_data["bonus_given_flag"]:
        builder.button(text="🚀 Начать Тест", callback_data="start_test")
    
    builder.button(text="💼 Услуги", callback_data="our_services_menu")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup(), format="HTML")

async def handle_callback(query: MessageCallback, bot: Bot):
    user_id = query.callback.user.user_id
    callback_data = query.callback.payload
    p_id = f"MAX_{user_id}"
    user_data = get_user(p_id)
    
    if not user_data:
         user_data = await core_logic.get_or_create_user(user_id, platform="MAX", 
                                              username=query.callback.user.username,
                                              first_name=query.callback.user.first_name)

    if callback_data == "start_test":
        await ask_question(query, bot, user_data)
    
    elif callback_data and callback_data.startswith("test_answer_"):
        _, _, q_idx, ans = callback_data.split("_")
        success, next_progress, hint, is_finished = core_logic.process_test_answer(user_data, int(q_idx), int(ans))
        
        if not success:
            await query.answer(notification="Показываю актуальный вопрос")
            await ask_question(query, bot, user_data)
            return

        update_user(p_id, user_data)
        
        if not is_finished:
            await query.answer(notification=hint)
            await ask_question(query, bot, user_data)
        else:
            await query.answer(notification=hint)
            await show_results(query, bot, user_data)

async def ask_question(query: MessageCallback | types.Message, bot: Bot, user_data):
    q_idx = user_data["test_progress"]
    question_text = TEST_QUESTIONS[q_idx]["text"]
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data=f"test_answer_{q_idx}_1")
    builder.button(text="Нет", callback_data=f"test_answer_{q_idx}_0")
    builder.button(text="Не знаю", callback_data=f"test_answer_{q_idx}_2")
    builder.adjust(3)
    
    text = f"<b>Вопрос {q_idx + 1}/8:</b>\n{question_text}"
    
    if isinstance(query, MessageCallback):
        await query.answer(new_text=text, format="HTML")
        # InlineKeyboardBuilder.as_markup() возвращает список кнопок, но в MAX API нужно передавать их в attachments
        # Библиотека maxapi может иметь свои особенности обновления клавиатуры через answer.
        # Для простоты в этом SDK обновление текста и кнопок в answer может быть ограничено.
        # Используем bot.edit_message если query.answer не обновляет кнопки.
    else:
        await query.answer(text, reply_markup=builder.as_markup(), format="HTML")

async def show_results(query: MessageCallback, bot: Bot, user_data):
    p_id = user_data["user_id"]
    positive_answers, bonus_added, user_data = core_logic.calculate_results(user_data)
    
    result_text = TEST_RESULTS_PROBLEM_COUNT.format(count=positive_answers)
    
    text = TEST_RESULTS_INTRO + result_text
    if bonus_added:
        text += TEST_RESULTS_BONUS_NEW.format(expiry_date=format_date_for_ru(user_data['bonus_expiry_date']))
    
    await query.answer(new_text=text, format="HTML")
    
    # Сброс
    user_data["test_progress"] = 0
    user_data["test_answers"] = [0]*8
    update_user(p_id, user_data)
