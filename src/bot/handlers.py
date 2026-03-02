"""Telegram bot handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import authorized_only
from src.common.logging import get_logger

logger = get_logger(__name__)


@authorized_only
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "Hallo! Ich bin der RvonGunten Office Bot.\n\n"
        "Sende mir:\n"
        "- Ein Foto eines Arbeitsrapports → Rechnung erstellen\n"
        "- Ein PDF (Bankbeleg/Rechnung) → Buchung erfassen\n\n"
        "/help für weitere Infos"
    )


@authorized_only
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "Befehle:\n"
        "/start - Bot starten\n"
        "/help - Diese Hilfe\n"
        "/status - Status der RPA-Jobs\n\n"
        "Dokumente:\n"
        "- Foto senden → Arbeitsrapport → Rechnung\n"
        "- PDF senden → Bankbeleg/Rechnung → Buchung"
    )


@authorized_only
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle received photos (Arbeitsrapporte)."""
    photo = update.message.photo[-1]  # Highest resolution
    file_id = photo.file_id

    logger.info("photo_received", file_id=file_id, chat_id=update.effective_chat.id)

    await update.message.reply_text(
        f"Foto erhalten (ID: {file_id[:8]}...).\n"
        "Extraktion wird in Phase 1 implementiert."
    )


@authorized_only
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle received documents (PDFs)."""
    document = update.message.document

    if document.mime_type != "application/pdf":
        await update.message.reply_text("Bitte nur PDF-Dateien senden.")
        return

    file_id = document.file_id
    logger.info("pdf_received", file_id=file_id, file_name=document.file_name)

    await update.message.reply_text(
        f"PDF erhalten: {document.file_name}\n"
        "Extraktion wird in Phase 3 implementiert."
    )


@authorized_only
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    await update.message.reply_text("Keine offenen Jobs.")
