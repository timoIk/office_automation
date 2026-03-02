"""Infoniqa ONE Start navigation via pywinauto.

Handles window management, field interaction, and menu navigation
for the Infoniqa ONE Start ERP (32-bit, UIA backend).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pyautogui
import pyperclip
from pywinauto import Desktop
from pywinauto.application import Application

from src.common.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InfoniqaError(Exception):
    """Base exception for Infoniqa RPA errors."""


class InfoniqaNotFoundError(InfoniqaError):
    """Infoniqa window could not be found or connected."""


class InfoniqaNavigationError(InfoniqaError):
    """Failed to navigate to the expected menu/form."""


class InfoniqaFieldError(InfoniqaError):
    """Failed to interact with a form field."""


class CustomerNotFoundError(InfoniqaError):
    """Customer name could not be resolved to an Infoniqa customer number."""


# ---------------------------------------------------------------------------
# Menu coordinate config (relative to the Infoniqa window)
# ---------------------------------------------------------------------------


@dataclass
class MenuCoordinates:
    """Click targets relative to the top-left corner of the Infoniqa window.

    These must be calibrated once on the target machine. The defaults are
    reasonable starting points for a 1920×1080 display with the window
    maximised.
    """

    # Main menu bar items
    kunden_menu: tuple[int, int] = (160, 50)
    # Sub-menu "Kundenbelege"
    kundenbelege: tuple[int, int] = (160, 180)
    # Context menu "Neu"
    neu: tuple[int, int] = (300, 180)
    # Fly-out "QR Rechnung"
    qr_rechnung: tuple[int, int] = (440, 210)


# ---------------------------------------------------------------------------
# Known automation IDs for CamEdit / button controls
# ---------------------------------------------------------------------------


@dataclass
class ControlIds:
    """Automation IDs for the invoice form controls."""

    customer_number: str = "9230"
    invoice_date: str = "7140"
    add_line_button: str = "1060"
    total_field: str = "9300"
    ok_button: str = "1"


# ---------------------------------------------------------------------------
# InfoniqaApp – main interface
# ---------------------------------------------------------------------------

# Window title substring used to locate the running application
_WINDOW_TITLE_PATTERN = "Infoniqa ONE Start"

# Expected tab title when a new invoice form is open
_INVOICE_TAB_TITLE = "Neues Kundendokument"


@dataclass
class InfoniqaApp:
    """Wrapper around a running Infoniqa ONE Start instance."""

    app: Application | None = field(default=None, repr=False)
    main_window: object | None = field(default=None, repr=False)
    menu_coords: MenuCoordinates = field(default_factory=MenuCoordinates)
    control_ids: ControlIds = field(default_factory=ControlIds)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def find_or_connect(self) -> None:
        """Attach to the running Infoniqa process via UIA backend."""
        try:
            self.app = Application(backend="uia").connect(
                title_re=f".*{_WINDOW_TITLE_PATTERN}.*",
                timeout=5,
            )
            self.main_window = self.app.window(title_re=f".*{_WINDOW_TITLE_PATTERN}.*")
            logger.info("infoniqa_connected", title=self.main_window.window_text())
        except Exception as exc:
            raise InfoniqaNotFoundError(
                f"Infoniqa ONE Start nicht gefunden: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Window helpers
    # ------------------------------------------------------------------

    def bring_to_front(self) -> None:
        """Bring Infoniqa to the foreground."""
        if self.main_window is None:
            raise InfoniqaNotFoundError("Nicht verbunden — find_or_connect() zuerst aufrufen.")
        try:
            self.main_window.set_focus()
            time.sleep(0.3)
        except Exception as exc:
            raise InfoniqaError(
                f"Fenster konnte nicht in den Vordergrund gebracht werden: {exc}"
            ) from exc

    def _window_rect(self) -> tuple[int, int, int, int]:
        """Return (left, top, right, bottom) of the main window."""
        rect = self.main_window.rectangle()
        return rect.left, rect.top, rect.right, rect.bottom

    def _abs_coords(self, rel: tuple[int, int]) -> tuple[int, int]:
        """Convert window-relative coordinates to absolute screen coordinates."""
        left, top, _, _ = self._window_rect()
        return left + rel[0], top + rel[1]

    # ------------------------------------------------------------------
    # Menu navigation
    # ------------------------------------------------------------------

    def navigate_to_new_invoice(self) -> None:
        """Open a new QR-Rechnung form via the menu.

        Uses pyautogui clicks on owner-drawn menus because UIA cannot
        read the menu text.
        """
        self.bring_to_front()
        time.sleep(0.3)

        steps = [
            ("kunden_menu", self.menu_coords.kunden_menu),
            ("kundenbelege", self.menu_coords.kundenbelege),
            ("neu", self.menu_coords.neu),
            ("qr_rechnung", self.menu_coords.qr_rechnung),
        ]

        for name, rel in steps:
            x, y = self._abs_coords(rel)
            logger.debug("menu_click", step=name, x=x, y=y)
            pyautogui.click(x, y)
            time.sleep(0.5)

        # Wait for the invoice tab to appear
        self.wait_for_invoice_tab(timeout=10)
        logger.info("invoice_form_opened")

    def wait_for_invoice_tab(self, timeout: int = 10) -> None:
        """Wait until the invoice tab title is visible."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                texts = [
                    child.window_text()
                    for child in self.main_window.children()
                    if hasattr(child, "window_text")
                ]
                if any(_INVOICE_TAB_TITLE in t for t in texts):
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise InfoniqaNavigationError(
            f"Rechnungsformular nicht innerhalb von {timeout}s geöffnet."
        )

    # ------------------------------------------------------------------
    # Field interaction
    # ------------------------------------------------------------------

    def set_field_value(self, auto_id: str, value: str) -> None:
        """Set a CamEdit field value using clipboard paste."""
        try:
            ctrl = self.main_window.child_window(auto_id=auto_id)
            ctrl.set_focus()
            time.sleep(0.15)
            # Select all existing text, then paste new value
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            safe_type_text(value)
            time.sleep(0.2)
        except InfoniqaFieldError:
            raise
        except Exception as exc:
            raise InfoniqaFieldError(
                f"Feld {auto_id} konnte nicht gesetzt werden: {exc}"
            ) from exc

    def click_control(self, auto_id: str) -> None:
        """Click a button or control by automation ID."""
        try:
            ctrl = self.main_window.child_window(auto_id=auto_id)
            ctrl.click_input()
            time.sleep(0.3)
        except Exception as exc:
            raise InfoniqaFieldError(
                f"Control {auto_id} konnte nicht geklickt werden: {exc}"
            ) from exc

    def wait_for_control(self, auto_id: str, timeout: int = 10) -> None:
        """Wait until a control with the given automation ID exists."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                ctrl = self.main_window.child_window(auto_id=auto_id)
                if ctrl.exists(timeout=0):
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise InfoniqaFieldError(
            f"Control {auto_id} nicht innerhalb von {timeout}s gefunden."
        )

    # ------------------------------------------------------------------
    # Popup / error detection
    # ------------------------------------------------------------------

    def check_for_popups(self) -> str | None:
        """Check for unexpected popup/error dialogs.

        Returns the popup text if one was found (and dismisses it with
        Escape), otherwise None.
        """
        try:
            desktop = Desktop(backend="uia")
            popups = desktop.windows(class_name_re=".*Popup.*|.*Dialog.*")
            for popup in popups:
                text = popup.window_text()
                if text and _WINDOW_TITLE_PATTERN in text:
                    logger.warning("popup_detected", text=text)
                    popup.set_focus()
                    pyautogui.press("escape")
                    time.sleep(0.3)
                    return text
        except Exception as exc:
            logger.debug("popup_check_failed", error=str(exc))
        return None


# ---------------------------------------------------------------------------
# Standalone helpers
# ---------------------------------------------------------------------------


def safe_type_text(text: str) -> None:
    """Type text via clipboard paste to handle German special characters."""
    old_clipboard = None
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        pass

    try:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
    except Exception as exc:
        raise InfoniqaFieldError(f"Text konnte nicht eingegeben werden: {exc}") from exc
    finally:
        # Restore previous clipboard content
        if old_clipboard is not None:
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass
