"""Job queue operations for RPA jobs."""

import json
from datetime import datetime

from sqlalchemy import select

from src.common.database import get_session
from src.common.models import RpaJobModel
from src.common.schemas import (
    BookingEntry,
    ExtractedInvoiceData,
    JobStatus,
    JobType,
    RpaJob,
)


def create_invoice_job(
    chat_id: int,
    message_id: int | None,
    invoice_data: ExtractedInvoiceData,
) -> RpaJob:
    """Create an invoice RPA job."""
    session = get_session()
    try:
        model = RpaJobModel(
            job_type=JobType.INVOICE,
            status=JobStatus.CONFIRMED,
            telegram_chat_id=chat_id,
            telegram_message_id=message_id,
            payload=invoice_data.model_dump_json(),
        )
        session.add(model)
        session.commit()
        session.refresh(model)

        return RpaJob(
            id=model.id,
            job_type=JobType.INVOICE,
            status=JobStatus.CONFIRMED,
            telegram_chat_id=chat_id,
            telegram_message_id=message_id,
            invoice_data=invoice_data,
        )
    finally:
        session.close()


def create_booking_job(
    chat_id: int,
    message_id: int | None,
    booking_entries: list[BookingEntry],
) -> RpaJob:
    """Create a booking RPA job."""
    session = get_session()
    try:
        payload = json.dumps([e.model_dump(mode="json") for e in booking_entries])
        model = RpaJobModel(
            job_type=JobType.BOOKING,
            status=JobStatus.CONFIRMED,
            telegram_chat_id=chat_id,
            telegram_message_id=message_id,
            payload=payload,
        )
        session.add(model)
        session.commit()
        session.refresh(model)

        return RpaJob(
            id=model.id,
            job_type=JobType.BOOKING,
            status=JobStatus.CONFIRMED,
            telegram_chat_id=chat_id,
            telegram_message_id=message_id,
            booking_entries=booking_entries,
        )
    finally:
        session.close()


def get_next_pending_job() -> RpaJob | None:
    """Get the next confirmed job for RPA execution."""
    session = get_session()
    try:
        stmt = (
            select(RpaJobModel)
            .where(RpaJobModel.status == JobStatus.CONFIRMED)
            .order_by(RpaJobModel.created_at)
            .limit(1)
        )
        model = session.execute(stmt).scalar_one_or_none()
        if model is None:
            return None

        job = RpaJob(
            id=model.id,
            job_type=JobType(model.job_type),
            status=JobStatus(model.status),
            telegram_chat_id=model.telegram_chat_id,
            telegram_message_id=model.telegram_message_id,
        )

        if model.job_type == JobType.INVOICE:
            job.invoice_data = ExtractedInvoiceData.model_validate_json(model.payload)
        elif model.job_type == JobType.BOOKING:
            entries = json.loads(model.payload)
            job.booking_entries = [BookingEntry.model_validate(e) for e in entries]

        return job
    finally:
        session.close()


def update_job_status(
    job_id: int,
    status: JobStatus,
    error_message: str | None = None,
) -> None:
    """Update job status."""
    session = get_session()
    try:
        model = session.get(RpaJobModel, job_id)
        if model is None:
            return
        model.status = status
        if error_message:
            model.error_message = error_message
        if status in (JobStatus.COMPLETED, JobStatus.FAILED):
            model.completed_at = datetime.now()
        session.commit()
    finally:
        session.close()
