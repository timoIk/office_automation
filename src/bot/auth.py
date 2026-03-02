"""Telegram user authorization."""

from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from src.common.config import get_settings
from src.common.logging import get_logger

logger = get_logger(__name__)


def authorized_only(func):
    """Decorator: Only allow configured Telegram user IDs."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        settings = get_settings()
        allowed = settings.allowed_user_id_list

        if not allowed:
            logger.warning("no_allowed_users_configured")
            await update.message.reply_text("Bot ist nicht konfiguriert. Keine User erlaubt.")
            return

        user_id = update.effective_user.id
        if user_id not in allowed:
            logger.warning("unauthorized_access", user_id=user_id)
            await update.message.reply_text("Nicht autorisiert.")
            return

        return await func(update, context)

    return wrapper
