"""Збірка повного результату розрахунку за місячним файлом."""

from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd

from ..config import CalculationSettings
from ..dataio import load_monthly_file, validate_frame
from ..models import SettlementResult
from .daily import build_daily
from .methodology import calculate_hourly


def calculate_settlement(
    df: pd.DataFrame,
    settings: CalculationSettings | None = None,
    source_name: str = "",
    warnings: list[str] | None = None,
) -> SettlementResult:
    """Розрахувати платіж за небаланси на вже прочитаній погодинній таблиці."""
    settings = settings or CalculationSettings()
    hours = calculate_hourly(df, settings)
    daily = build_daily(hours, settings.daily_threshold_uah)
    return SettlementResult(
        hours=hours,
        daily=daily,
        settings=settings,
        source_name=source_name,
        warnings=list(warnings or []),
    )


def calculate_from_file(
    source: str | Path | IO[bytes],
    settings: CalculationSettings | None = None,
    source_name: str = "",
) -> SettlementResult:
    """Прочитати файл ГП, перевірити його та виконати розрахунок."""
    frame = load_monthly_file(source)
    warnings = validate_frame(frame)
    name = source_name or (Path(source).name if isinstance(source, (str, Path)) else "")
    return calculate_settlement(frame, settings, name, warnings)


def recalculate(result: SettlementResult, settings: CalculationSettings) -> SettlementResult:
    """Перерахувати наявний результат з іншими параметрами (K_e, alpha, K_im, ПДВ)."""
    source_columns = [c for c in result.hours.columns if not c.startswith(("cieq", "w_alpha"))]
    return calculate_settlement(
        result.hours[source_columns],
        settings,
        result.source_name,
        result.warnings,
    )


def correction_payment(updated: SettlementResult, previous: SettlementResult) -> float:
    """Коригуючий платіж за главою 4 Порядку: різниця двох розрахунків, грн без ПДВ."""
    return updated.total_net - previous.total_net
