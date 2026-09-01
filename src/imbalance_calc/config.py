"""Константи та налаштування розрахунку.

Значення, що залежать від методики/періоду, винесені сюди, щоб їх можна було
змінити в одному місці або перевизначити зі змінних оточення.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
SAMPLES_DIR = DATA_DIR / "samples"

#: Поріг, вище якого доба потрапляє в окремий аналіз, грн.
DAILY_ALERT_THRESHOLD_UAH = Decimal(os.getenv("IC_DAILY_THRESHOLD", "10000"))

#: Тривалість розрахункового періоду (у хвилинах): 60 — година, 15 — квартагодина.
SETTLEMENT_PERIOD_MINUTES = int(os.getenv("IC_PERIOD_MINUTES", "60"))

#: Кількість знаків після коми при округленні грошових величин.
MONEY_ROUNDING = 2

#: Кількість знаків після коми при округленні обсягів, МВт·год.
VOLUME_ROUNDING = 6


@dataclass(frozen=True)
class CalculationSettings:
    """Параметри одного прогону розрахунку (задаються користувачем в UI)."""

    daily_threshold_uah: Decimal = DAILY_ALERT_THRESHOLD_UAH
    period_minutes: int = SETTLEMENT_PERIOD_MINUTES
    apply_vat: bool = False
    vat_rate: Decimal = Decimal("0.20")
    #: Довільні коефіцієнти методики, що можуть уточнюватись.
    coefficients: dict[str, Decimal] = field(default_factory=dict)
