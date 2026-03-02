"""Telegram bot handlers."""

import traceback

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.bot.auth import authorized_only
from src.common.database import get_session
from src.common.logging import get_logger
from src.common.models import DocumentModel, RpaJobModel
from src.common.schemas import JobStatus

logger = get_logger(__name__)


def _format_invoice_summary(data) -> str:
    """Format extracted invoice data as readable Telegram message."""
    lines = [
        f"Kunde: {data.customer_name}",
        f"Datum: {data.work_date}",
    ]
    if data.customer_address:
        lines.append(f"Adresse: {data.customer_address}")
    if data.description:
        lines.append(f"Arbeit: {data.description}")

    lines.append("\nPositionen:")
    for item in data.line_items:
        lines.append(f"  {item.position}. {item.description}")
        lines.append(f"     {item.quantity} {item.unit} × CHF {item.unit_price} = CHF {item.total}")

    lines.append(f"\nTotal: CHF {data.total_amount}")
    lines.append(f"Konfidenz: {data.confidence:.0%}")

    if data.notes:
        lines.append(f"\nBemerkungen: {data.notes}")

    return "\n".join(lines)


def _format_transactions_summary(transactions) -> str:
    """Format extracted transactions as readable Telegram message."""
    lines = [f"{len(transactions)} Transaktion(en) erkannt:\n"]
    for i, t in enumerate(transactions, 1):
        direction = "+" if t.is_credit else "-"
        lines.append(f"{i}. {t.transaction_date} | {direction} {t.currency} {t.amount}")
        lines.append(f"   {t.description}")
        if t.counterparty:
            lines.append(f"   Gegenpartei: {t.counterparty}")
    return "\n".join(lines)


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
    """Handle received photos (Arbeitsrapporte) — extract invoice data via Claude Vision."""
    from src.extraction.vision import ExtractionError, extract_invoice_from_photo

    photo = update.message.photo[-1]  # Highest resolution
    file_id = photo.file_id
    chat_id = update.effective_chat.id

    logger.info("photo_received", file_id=file_id, chat_id=chat_id)
    await update.message.reply_text("Foto erhalten. Extrahiere Daten...")

    try:
        # Download photo from Telegram
        file = await context.bot.get_file(file_id)
        image_bytes = await file.download_as_bytearray()

        # Save document record
        session = get_session()
        try:
            doc = DocumentModel(
                telegram_chat_id=chat_id,
                telegram_file_id=file_id,
                file_type="photo",
            )
            session.add(doc)
            session.commit()
        finally:
            session.close()

        # Extract via Claude Vision
        invoice_data = await extract_invoice_from_photo(bytes(image_bytes))

        # Store in context for confirmation callback
        context.user_data["pending_invoice"] = invoice_data
        context.user_data["pending_chat_id"] = chat_id
        context.user_data["pending_message_id"] = update.message.message_id

        summary = _format_invoice_summary(invoice_data)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Bestätigen", callback_data="confirm_invoice"),
                InlineKeyboardButton("❌ Verwerfen", callback_data="reject_invoice"),
            ]
        ])

        await update.message.reply_text(
            f"Extrahierte Rechnungsdaten:\n\n{summary}",
            reply_markup=keyboard,
        )

    except ExtractionError as e:
        logger.error("extraction_failed", error=str(e))
        await update.message.reply_text(f"Extraktion fehlgeschlagen: {e}")
    except Exception as e:
        logger.error("photo_handler_error", error=str(e), traceback=traceback.format_exc())
        await update.message.reply_text(f"Fehler bei der Verarbeitung: {e}")


@authorized_only
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle received documents (PDFs) — extract transactions via Claude Vision."""
    from src.extraction.vision import ExtractionError, extract_transactions_from_pdf

    document = update.message.document

    if document.mime_type != "application/pdf":
        await update.message.reply_text("Bitte nur PDF-Dateien senden.")
        return

    file_id = document.file_id
    chat_id = update.effective_chat.id

    logger.info("pdf_received", file_id=file_id, file_name=document.file_name)
    await update.message.reply_text(
        f"PDF erhalten: {document.file_name}\nExtrahiere Transaktionen..."
    )

    try:
        # Download PDF from Telegram
        file = await context.bot.get_file(file_id)
        pdf_bytes = await file.download_as_bytearray()

        # Save document record
        session = get_session()
        try:
            doc = DocumentModel(
                telegram_chat_id=chat_id,
                telegram_file_id=file_id,
                file_type="pdf",
            )
            session.add(doc)
            session.commit()
        finally:
            session.close()

        # Extract via Claude Vision
        transactions = await extract_transactions_from_pdf(bytes(pdf_bytes))

        if not transactions:
            await update.message.reply_text("Keine Transaktionen im Dokument erkannt.")
            return

        # Store for confirmation
        context.user_data["pending_transactions"] = transactions
        context.user_data["pending_chat_id"] = chat_id
        context.user_data["pending_message_id"] = update.message.message_id

        summary = _format_transactions_summary(transactions)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Bestätigen", callback_data="confirm_transactions"),
                InlineKeyboardButton("❌ Verwerfen", callback_data="reject_transactions"),
            ]
        ])

        await update.message.reply_text(
            f"Extrahierte Transaktionen:\n\n{summary}",
            reply_markup=keyboard,
        )

    except ExtractionError as e:
        logger.error("extraction_failed", error=str(e))
        await update.message.reply_text(f"Extraktion fehlgeschlagen: {e}")
    except Exception as e:
        logger.error("document_handler_error", error=str(e), traceback=traceback.format_exc())
        await update.message.reply_text(f"Fehler bei der Verarbeitung: {e}")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard callbacks for confirm/reject."""
    from src.common.queue import create_invoice_job

    query = update.callback_query
    await query.answer()

    if query.data == "confirm_invoice":
        invoice_data = context.user_data.get("pending_invoice")
        if not invoice_data:
            await query.edit_message_text("Keine ausstehenden Daten gefunden.")
            return

        chat_id = context.user_data.get("pending_chat_id")
        message_id = context.user_data.get("pending_message_id")

        job = create_invoice_job(chat_id, message_id, invoice_data)
        context.user_data.pop("pending_invoice", None)

        await query.edit_message_text(
            f"Rechnung bestätigt und Job #{job.id} erstellt.\n"
            "RPA-Verarbeitung gestartet. Du wirst benachrichtigt."
        )
        logger.info("invoice_confirmed", job_id=job.id)

    elif query.data == "reject_invoice":
        context.user_data.pop("pending_invoice", None)
        await query.edit_message_text("Rechnungsdaten verworfen.")
        logger.info("invoice_rejected")

    elif query.data == "confirm_transactions":
        transactions = context.user_data.get("pending_transactions")
        if not transactions:
            await query.edit_message_text("Keine ausstehenden Transaktionen gefunden.")
            return

        context.user_data.pop("pending_transactions", None)
        await query.edit_message_text(
            "Transaktionen bestätigt.\n"
            "Kontenzuordnung wird in Phase 3 implementiert."
        )
        logger.info("transactions_confirmed", count=len(transactions))

    elif query.data == "reject_transactions":
        context.user_data.pop("pending_transactions", None)
        await query.edit_message_text("Transaktionen verworfen.")
        logger.info("transactions_rejected")


@authorized_only
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command — show pending RPA jobs."""
    session = get_session()
    try:
        from sqlalchemy import select

        stmt = (
            select(RpaJobModel)
            .where(RpaJobModel.status.in_([
                JobStatus.PENDING,
                JobStatus.CONFIRMED,
                JobStatus.IN_PROGRESS,
            ]))
            .order_by(RpaJobModel.created_at.desc())
            .limit(10)
        )
        jobs = session.execute(stmt).scalars().all()

        if not jobs:
            await update.message.reply_text("Keine offenen Jobs.")
            return

        lines = ["Offene Jobs:\n"]
        for job in jobs:
            lines.append(
                f"#{job.id} | {job.job_type} | {job.status} | "
                f"{job.created_at.strftime('%d.%m.%Y %H:%M')}"
            )

        await update.message.reply_text("\n".join(lines))
    finally:
        session.close()
