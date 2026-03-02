"""Telegram bot application setup."""

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from src.bot.handlers import (
    document_handler,
    help_handler,
    photo_handler,
    start_handler,
    status_handler,
)
from src.common.config import get_settings
from src.common.logging import get_logger

logger = get_logger(__name__)


def create_bot_app():
    """Create and configure the Telegram bot application."""
    settings = get_settings()

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("status", status_handler))

    # Message handlers
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.PDF, document_handler))

    return app
