"""Tests for Pydantic schemas."""

from datetime import date
from decimal import Decimal

from src.common.schemas import (
    ExtractedInvoiceData,
    ExtractedTransaction,
    InvoiceLineItem,
    JobStatus,
    JobType,
    RpaJob,
)


def test_invoice_line_item_computed_total():
    item = InvoiceLineItem(
        description="Montage",
        quantity=Decimal("3.5"),
        unit_price=Decimal("85.00"),
        total=Decimal("297.50"),
    )
    assert item.computed_total == Decimal("297.50")


def test_extracted_invoice_data():
    data = ExtractedInvoiceData(
        customer_name="Müller AG",
        work_date=date(2026, 3, 1),
        line_items=[
            InvoiceLineItem(
                description="Sanitärarbeit",
                quantity=Decimal("2"),
                unit_price=Decimal("95.00"),
                total=Decimal("190.00"),
            )
        ],
        total_amount=Decimal("190.00"),
    )
    assert data.customer_name == "Müller AG"
    assert len(data.line_items) == 1
    assert data.total_amount == Decimal("190.00")


def test_extracted_transaction():
    tx = ExtractedTransaction(
        transaction_date=date(2026, 2, 28),
        description="COOP PRATTELN",
        amount=Decimal("45.30"),
        counterparty="Coop",
    )
    assert tx.currency == "CHF"
    assert not tx.is_credit


def test_rpa_job_defaults():
    job = RpaJob(
        job_type=JobType.INVOICE,
        telegram_chat_id=123,
    )
    assert job.status == JobStatus.PENDING
    assert job.invoice_data is None


def test_invoice_data_json_roundtrip():
    data = ExtractedInvoiceData(
        customer_name="Test",
        work_date=date(2026, 1, 15),
        line_items=[
            InvoiceLineItem(
                description="Arbeit",
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
                total=Decimal("100"),
            )
        ],
        total_amount=Decimal("100"),
    )
    json_str = data.model_dump_json()
    restored = ExtractedInvoiceData.model_validate_json(json_str)
    assert restored.customer_name == "Test"
    assert restored.line_items[0].unit_price == Decimal("100")
