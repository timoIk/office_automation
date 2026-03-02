# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Telegram bot for a small Swiss trades business (Handwerksbetrieb) that automates invoice creation and bookkeeping in Infoniqa ONE Start (Windows desktop ERP with no API). The pipeline: Telegram photo/PDF → Claude Vision extraction → human confirmation → RPA types data into Infoniqa.

Everything runs on the same Windows PC as Infoniqa — no network bridge needed.

## Commands

```bash
# Install dependencies (uv required)
uv pip install -e ".[dev]"        # core + dev tools
uv pip install -e ".[dev,rpa]"    # include pywinauto/pyautogui (Windows only)

# Run bot
python -m src.main

# Tests
.venv/bin/pytest                   # all tests
.venv/bin/pytest tests/test_schemas.py  # single file
.venv/bin/pytest -k "test_name"    # single test

# Lint
.venv/bin/ruff check src/ tests/
.venv/bin/ruff format src/ tests/

# Database migrations
.venv/bin/alembic upgrade head
.venv/bin/alembic revision --autogenerate -m "description"
```

## Architecture

### Data Flow

Two use cases share the same pipeline pattern:

1. **Invoice**: Photo of work report (Arbeitsrapport) → `extraction/` extracts via Claude Vision → user confirms in Telegram → `queue` creates RPA job → `rpa/infoniqa/` types invoice into ERP
2. **Booking**: Bank statement PDF or supplier invoice → `extraction/` extracts transactions → `booking/` suggests accounts (few-shot from history) → user confirms → RPA enters bookings

### Dual Schema Pattern

Data has two representations:
- **Pydantic schemas** (`src/common/schemas.py`): Used at runtime for extraction results, job definitions, API boundaries. `ExtractedInvoiceData`, `ExtractedTransaction`, `BookingEntry`, `RpaJob`.
- **SQLAlchemy models** (`src/common/models.py`): Persisted to SQLite. `RpaJobModel` stores job payload as JSON text. `BookingHistoryModel` feeds the account matcher.

The `RpaJobModel.payload` column stores serialized Pydantic data — `ExtractedInvoiceData.model_dump_json()` for invoices, JSON array of `BookingEntry` dicts for bookings. See `src/common/queue.py` for serialization/deserialization.

### Job Lifecycle

`JobStatus`: pending → confirmed (user approved) → in_progress (RPA working) → completed/failed

### Auth Model

All Telegram handlers use `@authorized_only` decorator (`src/bot/auth.py`) checking `ALLOWED_USER_IDS` env var. This is a single-user bot for one business.

### Configuration

All settings via `.env` file, loaded by pydantic-settings into `src/common/config.py`. Singleton pattern via `get_settings()`.

## Conventions

- All user-facing text in German (Swiss business context)
- Use `structlog` for logging (not stdlib logging)
- Use `Decimal` for monetary amounts, never float
- RPA modules use pywinauto primarily, pyautogui as fallback — deliberately no Claude Computer Use (cost, speed, data privacy)
- Ruff config: line-length 100, Python 3.12+ target

## Implementation Status

Phase 0 (foundation) is complete. Phases 1-4 are stubbed out:
- `src/extraction/vision.py` — Claude Vision wrapper (Phase 1)
- `src/booking/matcher.py` — Account matching with history + few-shot (Phase 3)
- `src/rpa/infoniqa/` — navigation.py, invoice.py, booking.py (Phases 2, 4)
