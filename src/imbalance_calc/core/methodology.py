"""Перерахунок вхідних даних відповідно до методики.

Тут зосереджені правила методики: приведення обсягів до розрахункових періодів,
застосування коефіцієнтів, нормалізація напрямку небалансу тощо.
Опис правил — у ``docs/methodology.md``.
"""

from __future__ import annotations

from ..config import CalculationSettings
from ..models import PeriodRecord


def recalculate(
    records: list[PeriodRecord],
    settings: CalculationSettings | None = None,
) -> list[PeriodRecord]:
    """Перерахувати вхідні записи за методикою.

    TODO: реалізувати кроки методики (уточнити з нормативним документом).
    """
    raise NotImplementedError
