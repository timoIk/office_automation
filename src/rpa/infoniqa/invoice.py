"""Invoice creation in Infoniqa via RPA.

Fills the QR-Rechnung form with extracted invoice data:
customer number, date, line items, then verifies total and saves.
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path

import pyautogui

from src.common.config import get_settings
from src.common.logging import get_logger
from src.common.schemas import ExtractedInvoiceData
from src.rpa.infoniqa.navigation import (
    CustomerNotFoundError,
    InfoniqaApp,
    InfoniqaError,
    InfoniqaFieldError,
    safe_type_text,
)

logger = get_logger(__name__)

# Re-export for convenience
__all__ = ["create_invoice", "CustomerNotFoundError"]


# ---------------------------------------------------------------------------
# Custom exception (declared in navigation for the hierarchy, but logically
# belongs to invoice operations)
# ---------------------------------------------------------------------------
# CustomerNotFoundError is defined in navigation.py to keep the exception
# hierarchy in one place. We import it above and re-export.


# ---------------------------------------------------------------------------
# Customer mapping helpers
# ---------------------------------------------------------------------------

_FUZZY_THRESHOLD = 0.75


def load_customer_map() -> dict[str, str]:
    """Load the customer name → Infoniqa customer number mapping."""
    path = Path(get_settings().customer_map_path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_customer_number(customer_name: str) -> str:
    """Resolve a customer name to an Infoniqa customer number.

    Tries exact match first, then fuzzy matching. Raises
    CustomerNotFoundError if no match is found.
    """
    mapping = load_customer_map()

    # Exact match (case-insensitive)
    name_lower = customer_name.strip().lower()
    for key, number in mapping.items():
        if key.strip().lower() == name_lower:
            logger.info("customer_exact_match", name=customer_name, number=number)
            return number

    # Fuzzy match
    best_ratio = 0.0
    best_key = ""
    best_number = ""
    for key, number in mapping.items():
        ratio = SequenceMatcher(None, name_lower, key.strip().lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_key = key
            best_number = number

    if best_ratio >= _FUZZY_THRESHOLD:
        logger.info(
            "customer_fuzzy_match",
            name=customer_name,
            matched=best_key,
            number=best_number,
            ratio=f"{best_ratio:.2f}",
        )
        return best_number

    raise CustomerNotFoundError(
        f"Kunde '{customer_name}' nicht in customer_map.json gefunden "
        f"(bester Match: '{best_key}' mit {best_ratio:.0%})."
    )


# ---------------------------------------------------------------------------
# Invoice creation
# ---------------------------------------------------------------------------


def create_invoice(invoice_data: ExtractedInvoiceData) -> str:
    """Create an invoice in Infoniqa from extracted data.

    Returns the document number (or a confirmation string) on success.
    Raises InfoniqaError subclasses on failure.
    """
    ina = InfoniqaApp()
    ina.find_or_connect()

    # Check for leftover dirty state
    popup_text = ina.check_for_popups()
    if popup_text:
        logger.warning("dismissed_popup_before_start", text=popup_text)

    # Resolve customer number before touching UI
    customer_number = resolve_customer_number(invoice_data.customer_name)

    # Open new invoice form
    ina.navigate_to_new_invoice()

    # Fill header
    _fill_header(ina, customer_number, invoice_data)

    # Fill line items
    _fill_line_items(ina, invoice_data)

    # Verify total
    _verify_total(ina, invoice_data.total_amount)

    # Save
    doc_number = _save_invoice(ina)

    logger.info(
        "invoice_created",
        customer=invoice_data.customer_name,
        total=str(invoice_data.total_amount),
        doc_number=doc_number,
    )
    return doc_number


# ---------------------------------------------------------------------------
# Internal steps
# ---------------------------------------------------------------------------


def _fill_header(
    ina: InfoniqaApp,
    customer_number: str,
    invoice_data: ExtractedInvoiceData,
) -> None:
    """Set customer number and invoice date in the header."""
    # Customer number — triggers auto-fill of address etc.
    ina.set_field_value(ina.control_ids.customer_number, customer_number)
    # Give Infoniqa time to auto-fill
    time.sleep(1.0)

    # Invoice date
    date_str = invoice_data.work_date.strftime("%d.%m.%Y")
    ina.set_field_value(ina.control_ids.invoice_date, date_str)
    time.sleep(0.3)

    logger.debug("header_filled", customer=customer_number, date=date_str)


def _fill_line_items(ina: InfoniqaApp, invoice_data: ExtractedInvoiceData) -> None:
    """Add each line item to the invoice grid.

    Each row: click "Hinzufügen", then Tab through columns:
    Menge → Einheit → Text → Einzelpreis
    """
    for item in invoice_data.line_items:
        # Click "Hinzufügen" button
        ina.click_control(ina.control_ids.add_line_button)
        time.sleep(0.5)

        # Tab through grid columns and fill values
        # Column order: Menge, Einheit, Text, Einzelpreis
        values = [
            str(item.quantity),
            item.unit,
            item.description,
            str(item.unit_price),
        ]

        for i, value in enumerate(values):
            safe_type_text(value)
            time.sleep(0.15)
            if i < len(values) - 1:
                pyautogui.press("tab")
                time.sleep(0.1)

        # Confirm row (Enter or Tab out)
        pyautogui.press("tab")
        time.sleep(0.3)

        logger.debug(
            "line_item_added",
            pos=item.position,
            desc=item.description,
            total=str(item.total),
        )


def _verify_total(ina: InfoniqaApp, expected_total: Decimal) -> None:
    """Read the total field and compare against the expected amount."""
    try:
        ctrl = ina.main_window.child_window(auto_id=ina.control_ids.total_field)
        raw_text = ctrl.get_value() if hasattr(ctrl, "get_value") else ctrl.window_text()

        # Parse Infoniqa total: may look like "1'234.50" or "1234.50"
        cleaned = raw_text.replace("'", "").replace("CHF", "").strip()
        if not cleaned:
            logger.warning("total_field_empty", raw=raw_text)
            return

        actual_total = Decimal(cleaned)
        if actual_total != expected_total:
            logger.warning(
                "total_mismatch",
                expected=str(expected_total),
                actual=str(actual_total),
            )
            raise InfoniqaFieldError(
                f"Total stimmt nicht überein: erwartet CHF {expected_total}, "
                f"Infoniqa zeigt CHF {actual_total}"
            )

        logger.info("total_verified", total=str(actual_total))

    except InfoniqaFieldError:
        raise
    except Exception as exc:
        logger.warning("total_verification_skipped", error=str(exc))


def _save_invoice(ina: InfoniqaApp) -> str:
    """Save the invoice via Ctrl+S and return a document reference."""
    pyautogui.hotkey("ctrl", "s")
    time.sleep(2.0)

    # Check for error popups after save
    popup = ina.check_for_popups()
    if popup:
        raise InfoniqaError(f"Fehler beim Speichern: {popup}")

    # Try to read the document number from the window title
    try:
        title = ina.main_window.window_text()
        # Title often contains the doc number after save
        if "Kundendokument" in title:
            return title.strip()
    except Exception:
        pass

    return "gespeichert"
