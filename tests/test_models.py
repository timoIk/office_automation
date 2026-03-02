"""Tests for SQLAlchemy models."""

from src.common.models import AccountModel, BookingHistoryModel, DocumentModel, RpaJobModel


def test_create_rpa_job(db_session):
    job = RpaJobModel(
        job_type="invoice",
        status="pending",
        telegram_chat_id=123,
        payload='{"test": true}',
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.id is not None
    assert job.job_type == "invoice"
    assert job.status == "pending"


def test_create_document(db_session):
    doc = DocumentModel(
        telegram_chat_id=123,
        telegram_file_id="abc123",
        file_type="photo",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert doc.id is not None


def test_create_booking_history(db_session):
    entry = BookingHistoryModel(
        transaction_date="2026-03-01",
        description="COOP PRATTELN",
        amount="45.30",
        counterparty="Coop",
        debit_account="4200",
        credit_account="1020",
        booking_text="Einkauf Material",
    )
    db_session.add(entry)
    db_session.commit()

    assert entry.id is not None


def test_create_account(db_session):
    acc = AccountModel(
        account_number="1020",
        account_name="Bank",
        account_type="Aktiv",
    )
    db_session.add(acc)
    db_session.commit()

    assert acc.id is not None
    assert acc.account_number == "1020"
