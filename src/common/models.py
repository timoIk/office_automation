"""SQLAlchemy models for persistent storage."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RpaJobModel(Base):
    """Persistierte RPA-Jobs."""

    __tablename__ = "rpa_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    telegram_chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # JSON-serialisierte Daten
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_rpa_jobs_status", "status"),)


class DocumentModel(Base):
    """Empfangene Dokumente (Fotos, PDFs)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # photo, pdf
    local_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class BookingHistoryModel(Base):
    """Historische Buchungen für Account Matching."""

    __tablename__ = "booking_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_date: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[str] = mapped_column(String(20), nullable=False)
    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    debit_account: Mapped[str] = mapped_column(String(10), nullable=False)
    credit_account: Mapped[str] = mapped_column(String(10), nullable=False)
    booking_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_booking_history_counterparty", "counterparty"),
        Index("ix_booking_history_description", "description"),
    )


class AccountModel(Base):
    """Kontenrahmen KMU."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Aktiv, Passiv, Aufwand, Ertrag
    parent_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
