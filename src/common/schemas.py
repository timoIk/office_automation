"""Pydantic schemas for API/extraction data."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


# --- Enums ---


class JobType(StrEnum):
    INVOICE = "invoice"
    BOOKING = "booking"


class JobStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# --- Arbeitsrapport / Invoice Schemas ---


class InvoiceLineItem(BaseModel):
    position: int = 1
    description: str
    quantity: Decimal = Decimal("1")
    unit: str = "Std."
    unit_price: Decimal
    total: Decimal

    @property
    def computed_total(self) -> Decimal:
        return self.quantity * self.unit_price


class ExtractedInvoiceData(BaseModel):
    """Extrahierte Daten aus einem Arbeitsrapport."""

    customer_name: str
    customer_address: str | None = None
    work_date: date
    description: str | None = None
    line_items: list[InvoiceLineItem]
    total_amount: Decimal
    notes: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


# --- Buchhaltung / Booking Schemas ---


class ExtractedTransaction(BaseModel):
    """Extrahierte Transaktion aus Bankbeleg oder Lieferantenrechnung."""

    transaction_date: date
    description: str
    amount: Decimal
    currency: str = "CHF"
    counterparty: str | None = None
    reference: str | None = None
    is_credit: bool = False


class AccountSuggestion(BaseModel):
    """Kontovorschlag für eine Buchung."""

    debit_account: str
    debit_account_name: str
    credit_account: str
    credit_account_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str | None = None


class BookingEntry(BaseModel):
    """Eine bestätigte Buchung."""

    transaction: ExtractedTransaction
    debit_account: str
    credit_account: str
    booking_text: str


# --- Job Schema ---


class RpaJob(BaseModel):
    """Ein RPA-Job zur Ausführung."""

    id: int | None = None
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    telegram_chat_id: int
    telegram_message_id: int | None = None
    invoice_data: ExtractedInvoiceData | None = None
    booking_entries: list[BookingEntry] | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
