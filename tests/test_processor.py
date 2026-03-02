"""Tests for src.rpa.processor."""

import sys
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Stub out RPA modules that are Windows-only
sys.modules.setdefault("pywinauto", MagicMock())
sys.modules.setdefault("pywinauto.application", MagicMock())
sys.modules.setdefault("pywinauto.Desktop", MagicMock())
sys.modules.setdefault("pyautogui", MagicMock())
sys.modules.setdefault("pyperclip", MagicMock())

from src.common.schemas import (  # noqa: E402
    ExtractedInvoiceData,
    InvoiceLineItem,
    JobStatus,
    JobType,
    RpaJob,
)


@pytest.fixture
def sample_job():
    return RpaJob(
        id=1,
        job_type=JobType.INVOICE,
        status=JobStatus.CONFIRMED,
        telegram_chat_id=123456,
        invoice_data=ExtractedInvoiceData(
            customer_name="Test AG",
            work_date=date(2026, 3, 1),
            line_items=[
                InvoiceLineItem(
                    position=1,
                    description="Arbeit",
                    quantity=Decimal("1"),
                    unit="Std.",
                    unit_price=Decimal("100"),
                    total=Decimal("100"),
                )
            ],
            total_amount=Decimal("100"),
        ),
    )


@pytest.fixture
def booking_job():
    return RpaJob(
        id=2,
        job_type=JobType.BOOKING,
        status=JobStatus.CONFIRMED,
        telegram_chat_id=123456,
        booking_entries=[],
    )


class TestProcessInvoiceJob:
    @pytest.mark.asyncio
    @patch("src.rpa.processor.update_job_status")
    @patch("src.rpa.processor.asyncio")
    async def test_success(self, mock_asyncio, mock_update, sample_job):
        from src.rpa.processor import _process_invoice_job

        # Make run_in_executor return a doc number
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value="RG-001")
        mock_asyncio.get_running_loop.return_value = mock_loop

        notify = AsyncMock()

        await _process_invoice_job(sample_job, notify)

        mock_update.assert_called_with(1, JobStatus.COMPLETED)
        notify.assert_called_once()
        assert "RG-001" in notify.call_args[0][1]

    @pytest.mark.asyncio
    @patch("src.rpa.processor.update_job_status")
    @patch("src.rpa.processor.asyncio")
    async def test_customer_not_found(self, mock_asyncio, mock_update, sample_job):
        from src.rpa.infoniqa.navigation import CustomerNotFoundError
        from src.rpa.processor import _process_invoice_job

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            side_effect=CustomerNotFoundError("not found")
        )
        mock_asyncio.get_running_loop.return_value = mock_loop

        notify = AsyncMock()

        await _process_invoice_job(sample_job, notify)

        mock_update.assert_called_with(1, JobStatus.FAILED, error_message="not found")
        notify.assert_called_once()
        assert "customer_map" in notify.call_args[0][1]

    @pytest.mark.asyncio
    @patch("src.rpa.processor.update_job_status")
    @patch("src.rpa.processor.asyncio")
    async def test_infoniqa_not_found(self, mock_asyncio, mock_update, sample_job):
        from src.rpa.infoniqa.navigation import InfoniqaNotFoundError
        from src.rpa.processor import _process_invoice_job

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            side_effect=InfoniqaNotFoundError("not running")
        )
        mock_asyncio.get_running_loop.return_value = mock_loop

        notify = AsyncMock()

        await _process_invoice_job(sample_job, notify)

        mock_update.assert_called_with(1, JobStatus.FAILED, error_message="not running")
        notify.assert_called_once()
        assert "Infoniqa nicht geöffnet" in notify.call_args[0][1]

    @pytest.mark.asyncio
    @patch("src.rpa.processor.update_job_status")
    @patch("src.rpa.processor.asyncio")
    async def test_generic_error(self, mock_asyncio, mock_update, sample_job):
        from src.rpa.processor import _process_invoice_job

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=RuntimeError("UI broke"))
        mock_asyncio.get_running_loop.return_value = mock_loop

        notify = AsyncMock()

        await _process_invoice_job(sample_job, notify)

        mock_update.assert_called_with(1, JobStatus.FAILED, error_message="UI broke")
        notify.assert_called_once()


class TestRunProcessor:
    @pytest.mark.asyncio
    @patch("src.rpa.processor.get_settings")
    @patch("src.rpa.processor.get_next_pending_job")
    @patch("src.rpa.processor.update_job_status")
    async def test_booking_job_marked_not_implemented(
        self, mock_update, mock_get_job, mock_settings, booking_job
    ):
        """Booking jobs should be marked as failed with Phase 4 message."""
        mock_settings.return_value.rpa_enabled = True
        mock_settings.return_value.rpa_poll_interval_seconds = 1

        # Return booking job once, then None to break the loop
        call_count = 0

        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return booking_job
            return None

        mock_get_job.side_effect = side_effect

        notify = AsyncMock()

        import asyncio

        from src.rpa.processor import run_processor

        task = asyncio.create_task(run_processor(notify))
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have set in_progress then failed
        assert mock_update.call_count >= 2
        mock_update.assert_any_call(2, JobStatus.IN_PROGRESS)
        mock_update.assert_any_call(
            2,
            JobStatus.FAILED,
            error_message="Buchungs-RPA noch nicht implementiert (Phase 4).",
        )
        notify.assert_called_once()
        assert "Phase 4" in notify.call_args[0][1]

    @pytest.mark.asyncio
    @patch("src.rpa.processor.get_settings")
    async def test_disabled_returns_immediately(self, mock_settings):
        """When rpa_enabled=False, the processor should return immediately."""
        mock_settings.return_value.rpa_enabled = False

        from src.rpa.processor import run_processor

        notify = AsyncMock()
        await run_processor(notify)
        notify.assert_not_called()
