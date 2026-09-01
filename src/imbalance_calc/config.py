"""Константи та налаштування розрахунку.

Параметри, яких немає у місячному файлі ГП (K_e, alpha, K_im, ПДВ), задаються
тут і можуть бути перевизначені зі змінних оточення або з UI.
Детальніше — docs/METHODOLOGY.md, розділ 9.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
SAMPLES_DIR = DATA_DIR / "samples"
STORE_DIR = Path(os.getenv("IC_STORE_DIR", DATA_DIR / "store"))
REPORTS_DIR = BASE_DIR / "reports"

#: Поріг, вище якого доба потрапляє в окремий аналіз, грн (без ПДВ).
DAILY_ALERT_THRESHOLD_UAH = float(os.getenv("IC_DAILY_THRESHOLD", "10000"))

#: Допустиме відхилення K_e для типу генерації ВДЕ, %.
DEFAULT_K_E = float(os.getenv("IC_K_E", "5"))

#: Частка відшкодування вартості врегулювання небалансу alpha_e, %.
DEFAULT_ALPHA = float(os.getenv("IC_ALPHA", "100"))

#: Коефіцієнт ціни небалансу K_im за Правилами ринку (частка, не відсотки).
#: Значення 0,05 звірене з виставленим рахунком за липень 2026 — див. розділ 13
#: docs/METHODOLOGY.md.
DEFAULT_K_IM = float(os.getenv("IC_K_IM", "0.05"))

#: Ставка ПДВ (частка).
DEFAULT_VAT_RATE = float(os.getenv("IC_VAT_RATE", "0.20"))

#: Округлення при виводі.
MONEY_ROUNDING = 2
VOLUME_ROUNDING = 6


@dataclass(frozen=True)
class CalculationSettings:
    """Параметри одного прогону розрахунку."""

    k_e: float = DEFAULT_K_E
    alpha: float = DEFAULT_ALPHA
    k_im: float = DEFAULT_K_IM
    vat_rate: float = DEFAULT_VAT_RATE
    daily_threshold_uah: float = DAILY_ALERT_THRESHOLD_UAH

    def describe(self) -> str:
        """Короткий опис параметрів для звіту."""
        threshold = f"{self.daily_threshold_uah:,.0f}".replace(",", " ")
        return (
            f"K_e = {self.k_e:g} %, "
            f"alpha = {self.alpha:g} %, "
            f"K_im = {self.k_im:g}, "
            f"ПДВ = {self.vat_rate * 100:g} %, "
            f"поріг доби = {threshold} грн"
        )
