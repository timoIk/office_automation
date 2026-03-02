"""Tests for extraction/vision.py — parsing logic (no API calls)."""

import json

import pytest

from src.extraction.vision import _parse_json_response


class TestParseJsonResponse:
    def test_plain_json(self):
        raw = '{"customer_name": "Müller AG", "total": "100.00"}'
        result = _parse_json_response(raw)
        assert result["customer_name"] == "Müller AG"

    def test_json_in_code_block(self):
        raw = '```json\n{"customer_name": "Test"}\n```'
        result = _parse_json_response(raw)
        assert result["customer_name"] == "Test"

    def test_json_array(self):
        raw = '[{"amount": "50.00"}, {"amount": "75.00"}]'
        result = _parse_json_response(raw)
        assert len(result) == 2
        assert result[0]["amount"] == "50.00"

    def test_json_array_in_code_block(self):
        raw = '```json\n[{"amount": "50.00"}]\n```'
        result = _parse_json_response(raw)
        assert isinstance(result, list)

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("not json at all")
