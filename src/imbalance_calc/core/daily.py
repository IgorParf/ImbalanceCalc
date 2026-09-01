"""Аналіз у розрізі діб, у т.ч. відбір діб із платежем понад поріг."""

from __future__ import annotations

from decimal import Decimal

from ..config import DAILY_ALERT_THRESHOLD_UAH
from ..models import DayResult, PeriodRecord


def build_daily_results(records: list[PeriodRecord]) -> list[DayResult]:
    """Згрупувати періоди по добах і порахувати добові підсумки."""
    raise NotImplementedError


def filter_alert_days(
    days: list[DayResult],
    threshold_uah: Decimal = DAILY_ALERT_THRESHOLD_UAH,
) -> list[DayResult]:
    """Повернути доби, платіж за які перевищує поріг (за замовчуванням 10 000 грн)."""
    raise NotImplementedError
