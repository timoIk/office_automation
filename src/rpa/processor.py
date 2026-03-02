"""Background job processor that polls confirmed jobs and dispatches to RPA."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor

from src.common.config import get_settings
from src.common.logging import get_logger
from src.common.queue import get_next_pending_job, update_job_status
from src.common.schemas import JobStatus, JobType

logger = get_logger(__name__)

# Type for the Telegram notification callback
NotifyCallback = Callable[[int, str], Awaitable[None]]

# Thread pool for blocking RPA calls
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rpa")


async def run_processor(notify: NotifyCallback) -> None:
    """Main processor loop — polls for confirmed jobs and executes RPA.

    Args:
        notify: async callback(chat_id, message_text) to send Telegram messages.
    """
    settings = get_settings()
    poll_interval = settings.rpa_poll_interval_seconds
    error_backoff_multiplier = 3

    if not settings.rpa_enabled:
        logger.info("rpa_disabled")
        return

    logger.info("rpa_processor_started", poll_interval=poll_interval)

    consecutive_errors = 0

    while True:
        try:
            job = get_next_pending_job()

            if job is None:
                consecutive_errors = 0
                await asyncio.sleep(poll_interval)
                continue

            logger.info("job_picked_up", job_id=job.id, job_type=job.job_type)

            # Mark as in_progress
            update_job_status(job.id, JobStatus.IN_PROGRESS)

            if job.job_type == JobType.INVOICE:
                await _process_invoice_job(job, notify)
            elif job.job_type == JobType.BOOKING:
                # Phase 4
                update_job_status(
                    job.id,
                    JobStatus.FAILED,
                    error_message="Buchungs-RPA noch nicht implementiert (Phase 4).",
                )
                await notify(
                    job.telegram_chat_id,
                    f"Job #{job.id}: Buchungs-RPA ist noch nicht verfügbar (Phase 4).",
                )
            else:
                update_job_status(
                    job.id,
                    JobStatus.FAILED,
                    error_message=f"Unbekannter Job-Typ: {job.job_type}",
                )

            consecutive_errors = 0

        except asyncio.CancelledError:
            logger.info("rpa_processor_cancelled")
            raise
        except Exception as exc:
            consecutive_errors += 1
            backoff = poll_interval * error_backoff_multiplier
            logger.error(
                "processor_error",
                error=str(exc),
                consecutive=consecutive_errors,
                backoff=backoff,
            )
            await asyncio.sleep(backoff)


async def _process_invoice_job(job, notify: NotifyCallback) -> None:
    """Process a single invoice job via RPA in a thread."""
    from src.rpa.infoniqa.invoice import create_invoice
    from src.rpa.infoniqa.navigation import CustomerNotFoundError, InfoniqaNotFoundError

    try:
        loop = asyncio.get_running_loop()
        doc_number = await loop.run_in_executor(
            _executor,
            create_invoice,
            job.invoice_data,
        )

        update_job_status(job.id, JobStatus.COMPLETED)
        await notify(
            job.telegram_chat_id,
            f"Rechnung erstellt: {doc_number}\n"
            f"(Job #{job.id}, Kunde: {job.invoice_data.customer_name})",
        )
        logger.info("job_completed", job_id=job.id, doc_number=doc_number)

    except CustomerNotFoundError as exc:
        msg = str(exc)
        update_job_status(job.id, JobStatus.FAILED, error_message=msg)
        await notify(
            job.telegram_chat_id,
            f"Job #{job.id} fehlgeschlagen: {msg}\n"
            "Bitte customer_map.json ergänzen und erneut bestätigen.",
        )
        logger.warning("customer_not_found", job_id=job.id, error=msg)

    except InfoniqaNotFoundError as exc:
        msg = str(exc)
        update_job_status(job.id, JobStatus.FAILED, error_message=msg)
        await notify(
            job.telegram_chat_id,
            f"Job #{job.id} fehlgeschlagen: Infoniqa nicht geöffnet.\n"
            "Bitte Infoniqa starten und Job erneut bestätigen.",
        )
        logger.error("infoniqa_not_found", job_id=job.id)

    except Exception as exc:
        msg = str(exc)
        update_job_status(job.id, JobStatus.FAILED, error_message=msg)
        await notify(
            job.telegram_chat_id,
            f"Job #{job.id} fehlgeschlagen: {msg}",
        )
        logger.error("job_failed", job_id=job.id, error=msg)
