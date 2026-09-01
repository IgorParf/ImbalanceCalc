"""Моделі даних, якими обмінюються шари пакета."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass
class PeriodRecord:
    """Один розрахунковий період (година або квартагодина)."""

    timestamp: datetime
    planned_mwh: Decimal          # заявлений (плановий) обсяг
    actual_mwh: Decimal           # фактичний обсяг
    imbalance_mwh: Decimal = Decimal("0")   # небаланс = факт - план
    price_uah_mwh: Decimal = Decimal("0")   # ціна врегулювання небалансу
    payment_uah: Decimal = Decimal("0")     # платіж за період


@dataclass
class DayResult:
    """Підсумок по добі."""

    day: date
    total_imbalance_mwh: Decimal
    positive_imbalance_mwh: Decimal
    negative_imbalance_mwh: Decimal
    payment_uah: Decimal
    exceeds_threshold: bool = False
    periods: list[PeriodRecord] = field(default_factory=list)


@dataclass
class SettlementResult:
    """Результат розрахунку за весь завантажений період."""

    periods: list[PeriodRecord] = field(default_factory=list)
    days: list[DayResult] = field(default_factory=list)
    total_payment_uah: Decimal = Decimal("0")
    total_imbalance_mwh: Decimal = Decimal("0")
    warnings: list[str] = field(default_factory=list)

    @property
    def alert_days(self) -> list[DayResult]:
        """Доби, платіж за які перевищує поріг."""
        return [d for d in self.days if d.exceeds_threshold]
