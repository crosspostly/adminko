from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from data_manager import get_user
from config import ADMIN_NOTIFICATION_CHAT_ID
from texts import (
    RETENTION_REVIEW_REQUEST,
    REVIEW_BONUS_MENU_TITLE,
    REVIEW_PROOF_RECEIVED,
    ADMIN_NEW_REVIEW_PROOF,
)

logger = logging.getLogger(__name__)

async def job_review_request(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends a message to the user asking for a review, 24 hours after a service.
    """
    user_id = context.job.user_id
    logger.info(f"Running review request job for user {user_id}")
    try:
        keyboard = [
            [InlineKeyboardButton("Оставить отзыв и получить бонусы", callback_data='get_review_bonuses')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id,
            text=RETENTION_REVIEW_REQUEST,
            reply_markup=reply_markup,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to send review request to user {user_id}: {e}")

async def get_review_bonuses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Displays the menu for submitting a review proof.
    """
    query = update.callback_query
    await query.answer()

    text = REVIEW_BONUS_MENU_TITLE
    keyboard = [
        [InlineKeyboardButton("↩️ Назад в личный кабинет", callback_data='personal_account_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    # Set state to await the review proof
    context.user_data['state'] = 'awaiting_review_proof'


async def handle_review_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles user's review proof (text or photo).
    Forwards it to the admin chat for verification.
    """
    if context.user_data.get('state') != 'awaiting_review_proof':
        # If we are not waiting for a review, do nothing.
        # This allows other text/photo handlers to work.
        return

    user = update.effective_user
    p_id = f"TG_{user.id}"
    user_data = get_user(p_id)
    
    if not user_data:
        await update.message.reply_text("Произошла ошибка. Пожалуйста, начните с команды /start.")
        return

    admin_caption = ADMIN_NEW_REVIEW_PROOF.format(
        first_name=user.first_name,
        user_id=user.id,
        username=user.username or 'N/A'
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить (Яндекс)", callback_data=f'verify_review_approve_{user.id}_yandex'),
            InlineKeyboardButton("✅ Одобрить (2GIS)", callback_data=f'verify_review_approve_{user.id}_2gis')
        ],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f'verify_review_reject_{user.id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.message.photo:
            # Forward the photo
            await context.bot.send_photo(
                chat_id=ADMIN_NOTIFICATION_CHAT_ID,
                photo=update.message.photo[-1].file_id,
                caption=admin_caption,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        elif update.message.text:
            # Forward the text
            forward_text = f"<blockquote>{update.message.text}</blockquote>"
            await context.bot.send_message(
                chat_id=ADMIN_NOTIFICATION_CHAT_ID,
                text=admin_caption + "\n\n" + forward_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        # Confirm to user and clear state
        await update.message.reply_text(REVIEW_PROOF_RECEIVED)
        context.user_data['state'] = None

    except Exception as e:
        logger.error(f"Failed to forward review proof from user {user.id}: {e}")
        await update.message.reply_text("Произошла ошибка при отправке вашего отзыва. Пожалуйста, попробуйте еще раз.")
