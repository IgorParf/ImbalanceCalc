"""Формування підсумкового результату розрахунку."""

from __future__ import annotations

from ..config import CalculationSettings
from ..models import PeriodRecord, SettlementResult


def calculate_settlement(
    records: list[PeriodRecord],
    settings: CalculationSettings | None = None,
) -> SettlementResult:
    """Розрахувати загальний платіж за небаланси та підсумки по добах.

    Порядок: перерахунок за методикою -> небаланс по періодах -> платіж по
    періодах -> агрегація по добах -> позначення діб понад поріг -> загальний підсумок.
    """
    raise NotImplementedError
