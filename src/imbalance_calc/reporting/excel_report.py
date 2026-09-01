"""Вивантаження результату в Excel."""

from __future__ import annotations

from pathlib import Path

from ..models import SettlementResult


def build_excel_report(result: SettlementResult, path: str | Path) -> Path:
    """Записати звіт у xlsx: аркуші «Періоди», «По добах», «Понад 10 000 грн», «Підсумок»."""
    raise NotImplementedError


def build_excel_bytes(result: SettlementResult) -> bytes:
    """Той самий звіт у пам'яті — для кнопки завантаження в UI."""
    raise NotImplementedError
