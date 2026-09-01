"""Обчислення обсягу небалансу та ціни його врегулювання."""

from __future__ import annotations

from decimal import Decimal

from ..models import PeriodRecord


def calculate_imbalance(record: PeriodRecord) -> Decimal:
    """Небаланс за період: фактичний обсяг мінус заявлений, МВт·год.

    Додатне значення — надлишок (небаланс "+"), від'ємне — дефіцит (небаланс "-").
    """
    raise NotImplementedError


def calculate_period_payment(record: PeriodRecord) -> Decimal:
    """Платіж за один розрахунковий період, грн.

    TODO: врахувати різні ціни для додатного та від'ємного небалансу.
    """
    raise NotImplementedError
