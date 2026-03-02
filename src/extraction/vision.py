"""Claude Vision wrapper for document extraction."""

import base64
import json
from decimal import Decimal

import anthropic
import fitz  # pymupdf

from src.common.config import get_settings
from src.common.logging import get_logger
from src.common.schemas import ExtractedInvoiceData, ExtractedTransaction, InvoiceLineItem

logger = get_logger(__name__)

INVOICE_EXTRACTION_PROMPT = """\
Du erhältst ein Foto eines Arbeitsrapports (Handwerk/Bau, Schweiz).
Extrahiere die folgenden Informationen als JSON:

{
  "customer_name": "Name des Kunden",
  "customer_address": "Adresse falls vorhanden, sonst null",
  "work_date": "YYYY-MM-DD",
  "description": "Kurzbeschreibung der Arbeit",
  "line_items": [
    {
      "position": 1,
      "description": "Beschreibung der Position",
      "quantity": "1.0",
      "unit": "Std.",
      "unit_price": "85.00",
      "total": "85.00"
    }
  ],
  "total_amount": "85.00",
  "notes": "Zusätzliche Bemerkungen, sonst null",
  "confidence": 0.85
}

Regeln:
- Alle Beträge als Strings mit 2 Dezimalstellen (z.B. "85.00")
- Datum im Format YYYY-MM-DD
- Einheiten: "Std." (Stunden), "Stk." (Stück), "m", "m²", "Pauschale"
- confidence: 0.0 bis 1.0 — wie sicher bist du bei der Extraktion?
- Falls etwas unleserlich ist, setze confidence tiefer und notiere es in notes
- Antworte NUR mit dem JSON, kein anderer Text"""

TRANSACTION_EXTRACTION_PROMPT = """\
Du erhältst ein Dokument (Bankbeleg, Kontoauszug oder Lieferantenrechnung, Schweiz).
Extrahiere alle Transaktionen als JSON-Array:

[
  {
    "transaction_date": "YYYY-MM-DD",
    "description": "Beschreibung/Verwendungszweck",
    "amount": "150.00",
    "currency": "CHF",
    "counterparty": "Name der Gegenpartei falls erkennbar, sonst null",
    "reference": "Referenznummer falls vorhanden, sonst null",
    "is_credit": false
  }
]

Regeln:
- Beträge als Strings mit 2 Dezimalstellen
- is_credit: true = Gutschrift/Eingang, false = Belastung/Ausgang
- Bei Lieferantenrechnungen: eine Transaktion mit dem Totalbetrag
- Antworte NUR mit dem JSON-Array, kein anderer Text"""


def _get_client() -> anthropic.Anthropic:
    """Create Anthropic client."""
    settings = get_settings()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _encode_image(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """Encode image bytes to base64 for Claude API."""
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        },
    }


def _pdf_to_images(pdf_bytes: bytes, max_pages: int = 10) -> list[bytes]:
    """Convert PDF pages to PNG images using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page_num in range(min(len(doc), max_pages)):
        page = doc[page_num]
        # 2x zoom for better OCR quality
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def _parse_json_response(text: str) -> dict | list:
    """Parse JSON from Claude response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        # Remove markdown code block
        lines = text.split("\n")
        # Remove first and last line (```json and ```)
        lines = [line for line in lines[1:] if not line.strip() == "```"]
        text = "\n".join(lines)
    return json.loads(text)


async def extract_invoice_from_photo(image_bytes: bytes) -> ExtractedInvoiceData:
    """Extract invoice data from a photo of an Arbeitsrapport.

    Args:
        image_bytes: JPEG/PNG image bytes from Telegram.

    Returns:
        ExtractedInvoiceData with extracted fields.

    Raises:
        ExtractionError: If extraction or parsing fails.
    """
    client = _get_client()
    logger.info("extracting_invoice", image_size=len(image_bytes))

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    _encode_image(image_bytes, "image/jpeg"),
                    {"type": "text", "text": INVOICE_EXTRACTION_PROMPT},
                ],
            }
        ],
    )

    raw = _parse_json_response(message.content[0].text)
    logger.info("invoice_extracted", customer=raw.get("customer_name"))

    # Convert to Pydantic model with Decimal handling
    line_items = [
        InvoiceLineItem(
            position=item.get("position", i + 1),
            description=item["description"],
            quantity=Decimal(str(item["quantity"])),
            unit=item.get("unit", "Std."),
            unit_price=Decimal(str(item["unit_price"])),
            total=Decimal(str(item["total"])),
        )
        for i, item in enumerate(raw["line_items"])
    ]

    return ExtractedInvoiceData(
        customer_name=raw["customer_name"],
        customer_address=raw.get("customer_address"),
        work_date=raw["work_date"],
        description=raw.get("description"),
        line_items=line_items,
        total_amount=Decimal(str(raw["total_amount"])),
        notes=raw.get("notes"),
        confidence=float(raw.get("confidence", 0.8)),
    )


async def extract_transactions_from_pdf(pdf_bytes: bytes) -> list[ExtractedTransaction]:
    """Extract transactions from a PDF (bank statement or supplier invoice).

    Args:
        pdf_bytes: PDF file bytes from Telegram.

    Returns:
        List of ExtractedTransaction objects.

    Raises:
        ExtractionError: If extraction or parsing fails.
    """
    client = _get_client()
    images = _pdf_to_images(pdf_bytes)
    logger.info("extracting_transactions", pages=len(images))

    # Build content with all page images
    content: list[dict] = []
    for img_bytes in images:
        content.append(_encode_image(img_bytes, "image/png"))
    content.append({"type": "text", "text": TRANSACTION_EXTRACTION_PROMPT})

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": content}],
    )

    raw_list = _parse_json_response(message.content[0].text)
    logger.info("transactions_extracted", count=len(raw_list))

    transactions = []
    for raw in raw_list:
        transactions.append(
            ExtractedTransaction(
                transaction_date=raw["transaction_date"],
                description=raw["description"],
                amount=Decimal(str(raw["amount"])),
                currency=raw.get("currency", "CHF"),
                counterparty=raw.get("counterparty"),
                reference=raw.get("reference"),
                is_credit=raw.get("is_credit", False),
            )
        )

    return transactions


class ExtractionError(Exception):
    """Raised when document extraction fails."""

    pass
