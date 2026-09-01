"""Перетворення результату розрахунку у таблиці та текстові підсумки."""

from __future__ import annotations

import pandas as pd

from ..models import SettlementResult


def result_to_frames(result: SettlementResult) -> dict[str, pd.DataFrame]:
    """Повернути набір таблиць: ``periods``, ``daily``, ``alert_days``, ``totals``."""
    raise NotImplementedError


def summary_text(result: SettlementResult) -> str:
    """Короткий текстовий підсумок: загальний платіж, обсяг, кількість діб понад поріг."""
    raise NotImplementedError
