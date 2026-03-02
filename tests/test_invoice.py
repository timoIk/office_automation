"""Tests for src.rpa.infoniqa.invoice."""

import json
import sys
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

# Stub out RPA modules that are Windows-only
sys.modules.setdefault("pywinauto", MagicMock())
sys.modules.setdefault("pywinauto.application", MagicMock())
sys.modules.setdefault("pywinauto.Desktop", MagicMock())
sys.modules.setdefault("pyautogui", MagicMock())
sys.modules.setdefault("pyperclip", MagicMock())

from src.common.schemas import ExtractedInvoiceData, InvoiceLineItem  # noqa: E402
from src.rpa.infoniqa.navigation import CustomerNotFoundError  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_invoice():
    return ExtractedInvoiceData(
        customer_name="Müller AG",
        work_date=date(2026, 3, 1),
        line_items=[
            InvoiceLineItem(
                position=1,
                description="Sanitärarbeit",
                quantity=Decimal("3"),
                unit="Std.",
                unit_price=Decimal("120.00"),
                total=Decimal("360.00"),
            ),
            InvoiceLineItem(
                position=2,
                description="Material Kupferrohr",
                quantity=Decimal("1"),
                unit="Psch.",
                unit_price=Decimal("85.50"),
                total=Decimal("85.50"),
            ),
        ],
        total_amount=Decimal("445.50"),
    )


@pytest.fixture
def customer_map_file(tmp_path):
    """Create a temp customer_map.json and patch settings to use it."""
    path = tmp_path / "customer_map.json"
    data = {
        "Müller AG": "10001",
        "Bäckerei Schneider": "10002",
        "Meier & Söhne GmbH": "10003",
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Customer lookup tests
# ---------------------------------------------------------------------------


class TestResolveCustomerNumber:
    def _get_resolve(self):
        from src.rpa.infoniqa.invoice import resolve_customer_number

        return resolve_customer_number

    def test_exact_match(self, customer_map_file):
        with patch("src.rpa.infoniqa.invoice.get_settings") as mock_settings:
            mock_settings.return_value.customer_map_path = str(customer_map_file)
            resolve = self._get_resolve()
            assert resolve("Müller AG") == "10001"

    def test_case_insensitive(self, customer_map_file):
        with patch("src.rpa.infoniqa.invoice.get_settings") as mock_settings:
            mock_settings.return_value.customer_map_path = str(customer_map_file)
            resolve = self._get_resolve()
            assert resolve("müller ag") == "10001"

    def test_fuzzy_match(self, customer_map_file):
        with patch("src.rpa.infoniqa.invoice.get_settings") as mock_settings:
            mock_settings.return_value.customer_map_path = str(customer_map_file)
            resolve = self._get_resolve()
            # "Meier und Söhne GmbH" is close to "Meier & Söhne GmbH"
            assert resolve("Meier und Söhne GmbH") == "10003"

    def test_no_match_raises(self, customer_map_file):
        with patch("src.rpa.infoniqa.invoice.get_settings") as mock_settings:
            mock_settings.return_value.customer_map_path = str(customer_map_file)
            resolve = self._get_resolve()
            with pytest.raises(CustomerNotFoundError, match="nicht in customer_map"):
                resolve("Völlig Unbekannt GmbH")

    def test_empty_map_raises(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("{}", encoding="utf-8")
        with patch("src.rpa.infoniqa.invoice.get_settings") as mock_settings:
            mock_settings.return_value.customer_map_path = str(path)
            resolve = self._get_resolve()
            with pytest.raises(CustomerNotFoundError):
                resolve("Anyone")

    def test_missing_file_raises(self, tmp_path):
        with patch("src.rpa.infoniqa.invoice.get_settings") as mock_settings:
            mock_settings.return_value.customer_map_path = str(tmp_path / "missing.json")
            resolve = self._get_resolve()
            with pytest.raises(CustomerNotFoundError):
                resolve("Test")


# ---------------------------------------------------------------------------
# Full create_invoice sequence (mocked RPA)
# ---------------------------------------------------------------------------


class TestCreateInvoice:
    @patch("src.rpa.infoniqa.invoice._save_invoice", return_value="RG-2026-001")
    @patch("src.rpa.infoniqa.invoice._verify_total")
    @patch("src.rpa.infoniqa.invoice._fill_line_items")
    @patch("src.rpa.infoniqa.invoice._fill_header")
    @patch("src.rpa.infoniqa.invoice.resolve_customer_number", return_value="10001")
    @patch("src.rpa.infoniqa.invoice.InfoniqaApp")
    def test_happy_path(
        self,
        mock_app_cls,
        mock_resolve,
        mock_header,
        mock_lines,
        mock_verify,
        mock_save,
        sample_invoice,
    ):
        from src.rpa.infoniqa.invoice import create_invoice

        mock_app = mock_app_cls.return_value
        mock_app.check_for_popups.return_value = None

        result = create_invoice(sample_invoice)

        assert result == "RG-2026-001"
        mock_app.find_or_connect.assert_called_once()
        mock_app.navigate_to_new_invoice.assert_called_once()
        mock_resolve.assert_called_once_with("Müller AG")
        mock_header.assert_called_once()
        mock_lines.assert_called_once()
        mock_verify.assert_called_once()
        mock_save.assert_called_once()

    @patch("src.rpa.infoniqa.invoice.resolve_customer_number")
    @patch("src.rpa.infoniqa.invoice.InfoniqaApp")
    def test_customer_not_found_aborts(self, mock_app_cls, mock_resolve, sample_invoice):
        from src.rpa.infoniqa.invoice import create_invoice

        mock_app = mock_app_cls.return_value
        mock_app.check_for_popups.return_value = None
        mock_resolve.side_effect = CustomerNotFoundError("not found")

        with pytest.raises(CustomerNotFoundError):
            create_invoice(sample_invoice)

        # Should NOT have tried to navigate since customer resolution failed
        mock_app.navigate_to_new_invoice.assert_not_called()
