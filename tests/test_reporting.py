"""Тести формування звітів."""

from __future__ import annotations

from imbalance_calc.core import calculate_settlement
from imbalance_calc.reporting import (
    build_excel_bytes,
    build_pdf_bytes,
    build_pdf_report,
    compare,
    daily_display,
    money,
    summary_text,
)


def test_money_uses_ukrainian_separators():
    assert money(1234567.891) == "1 234 567,89".replace(" ", " ")


def test_pdf_is_generated(frame):
    payload = build_pdf_bytes(calculate_settlement(frame))
    assert payload.startswith(b"%PDF")
    assert len(payload) > 10_000


def test_pdf_is_saved_to_directory(frame, tmp_path):
    path = build_pdf_report(calculate_settlement(frame), tmp_path)
    assert path.exists()
    assert path.suffix == ".pdf"
    assert path.parent == tmp_path


def test_excel_is_generated(frame):
    payload = build_excel_bytes(calculate_settlement(frame))
    assert payload[:2] == b"PK"


def test_summary_mentions_vat(frame):
    text = summary_text(calculate_settlement(frame))
    assert "ПДВ" in text
    assert "липень 2026" in text


def test_daily_display_has_ukrainian_headers(frame):
    columns = list(daily_display(calculate_settlement(frame)).columns)
    assert "Платіж, грн" in columns
    assert "Понад поріг" in columns


def test_compare_same_month_disambiguates_labels(frame):
    result = calculate_settlement(frame)
    frame_out = compare(result, result)
    assert "липень 2026 (1)" in frame_out.columns
    assert "липень 2026 (2)" in frame_out.columns
