import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from texts import TEST_OFFER_REMINDER

logger = logging.getLogger(__name__)

async def delete_message_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes a specific message."""
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message_id = job_data['message_id']
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Deleted test offer message {message_id} for user {chat_id}")
    except Exception as e:
        logger.warning(f"Could not delete message {message_id} for user {chat_id}: {e}")

async def send_test_offer_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message offering the test and schedules its deletion."""
    from data_manager import get_user
    
    job_data = context.job.data
    user_id = job_data['user_id']
    
    # Check if the user has already taken the test
    user_data = get_user(user_id)
    if not user_data or user_data.get("bonus_given_flag"):
        logger.info(f"Skipping test offer for user {user_id} who has already completed it.")
        return

    try:
        keyboard = [[InlineKeyboardButton("🚀 Пройти Экспресс-тест", callback_data='start_test')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_message = await context.bot.send_message(
            chat_id=user_id, 
            text=TEST_OFFER_REMINDER, 
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        logger.info(f"Sent test offer message to user {user_id}")

        # Schedule the deletion of this message
        context.job_queue.run_once(
            delete_message_job, 
            when=43200,  # 12 hours in seconds
            data={'chat_id': user_id, 'message_id': sent_message.message_id},
            name=f"delete_offer_{user_id}_{sent_message.message_id}"
        )

    except Exception as e:
        logger.error(f"Failed to send test offer to user {user_id}: {e}")
