"""Звіти: PDF (основний формат), Excel та підсумкові таблиці."""

from .excel_report import build_excel_bytes, build_excel_report
from .pdf_report import build_pdf_bytes, build_pdf_report, report_filename
from .summary import (
    compare,
    daily_comparison,
    daily_display,
    hourly_display,
    money,
    summary_text,
    totals_rows,
    volume,
)

__all__ = [
    "build_pdf_report",
    "build_pdf_bytes",
    "report_filename",
    "build_excel_report",
    "build_excel_bytes",
    "totals_rows",
    "daily_display",
    "hourly_display",
    "summary_text",
    "compare",
    "daily_comparison",
    "money",
    "volume",
]
