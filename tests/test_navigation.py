"""Tests for src.rpa.infoniqa.navigation."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Stub out RPA modules that are Windows-only
sys.modules.setdefault("pywinauto", MagicMock())
sys.modules.setdefault("pywinauto.application", MagicMock())
sys.modules.setdefault("pywinauto.Desktop", MagicMock())
sys.modules.setdefault("pyautogui", MagicMock())
sys.modules.setdefault("pyperclip", MagicMock())

from src.rpa.infoniqa.navigation import (  # noqa: E402
    ControlIds,
    CustomerNotFoundError,
    InfoniqaApp,
    InfoniqaError,
    InfoniqaFieldError,
    InfoniqaNavigationError,
    InfoniqaNotFoundError,
    MenuCoordinates,
    safe_type_text,
)


class TestExceptions:
    """Exception hierarchy tests."""

    def test_base_exception(self):
        assert issubclass(InfoniqaError, Exception)

    def test_not_found_is_infoniqa_error(self):
        assert issubclass(InfoniqaNotFoundError, InfoniqaError)

    def test_navigation_is_infoniqa_error(self):
        assert issubclass(InfoniqaNavigationError, InfoniqaError)

    def test_field_is_infoniqa_error(self):
        assert issubclass(InfoniqaFieldError, InfoniqaError)

    def test_customer_not_found_is_infoniqa_error(self):
        assert issubclass(CustomerNotFoundError, InfoniqaError)

    def test_exception_message(self):
        exc = InfoniqaNotFoundError("test message")
        assert str(exc) == "test message"


class TestMenuCoordinates:
    """MenuCoordinates dataclass tests."""

    def test_defaults(self):
        mc = MenuCoordinates()
        assert isinstance(mc.kunden_menu, tuple)
        assert len(mc.kunden_menu) == 2

    def test_custom_coords(self):
        mc = MenuCoordinates(kunden_menu=(100, 200))
        assert mc.kunden_menu == (100, 200)


class TestControlIds:
    """ControlIds dataclass tests."""

    def test_defaults(self):
        ids = ControlIds()
        assert ids.customer_number == "9230"
        assert ids.invoice_date == "7140"
        assert ids.add_line_button == "1060"
        assert ids.total_field == "9300"

    def test_custom_ids(self):
        ids = ControlIds(customer_number="1234")
        assert ids.customer_number == "1234"


class TestSafeTypeText:
    """safe_type_text tests with mocked clipboard."""

    @patch("src.rpa.infoniqa.navigation.pyperclip")
    @patch("src.rpa.infoniqa.navigation.pyautogui")
    def test_pastes_via_clipboard(self, mock_pyautogui, mock_pyperclip):
        mock_pyperclip.paste.return_value = "old"

        safe_type_text("Hütte & Söhne")

        mock_pyperclip.copy.assert_any_call("Hütte & Söhne")
        mock_pyautogui.hotkey.assert_called_with("ctrl", "v")
        # Old clipboard should be restored
        mock_pyperclip.copy.assert_called_with("old")

    @patch("src.rpa.infoniqa.navigation.pyperclip")
    @patch("src.rpa.infoniqa.navigation.pyautogui")
    def test_raises_field_error_on_failure(self, mock_pyautogui, mock_pyperclip):
        mock_pyperclip.paste.return_value = ""
        mock_pyperclip.copy.side_effect = [None, None]
        mock_pyautogui.hotkey.side_effect = RuntimeError("no display")

        with pytest.raises(InfoniqaFieldError, match="Text konnte nicht"):
            safe_type_text("test")


class TestInfoniqaApp:
    """InfoniqaApp basic tests."""

    def test_abs_coords(self):
        ina = InfoniqaApp()
        # Mock main_window with a rectangle
        mock_window = MagicMock()
        mock_rect = MagicMock()
        mock_rect.left = 100
        mock_rect.top = 50
        mock_rect.right = 1100
        mock_rect.bottom = 850
        mock_window.rectangle.return_value = mock_rect
        ina.main_window = mock_window

        result = ina._abs_coords((160, 50))
        assert result == (260, 100)

    def test_bring_to_front_raises_without_connection(self):
        ina = InfoniqaApp()
        with pytest.raises(InfoniqaNotFoundError, match="Nicht verbunden"):
            ina.bring_to_front()
