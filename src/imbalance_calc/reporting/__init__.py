"""Формування звітів та підсумкових таблиць."""

from .excel_report import build_excel_report
from .summary import result_to_frames, summary_text

__all__ = ["build_excel_report", "result_to_frames", "summary_text"]
