"""Моделі даних, якими обмінюються шари пакета."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .config import CalculationSettings

UKR_MONTHS = {
    1: "січень", 2: "лютий", 3: "березень", 4: "квітень",
    5: "травень", 6: "червень", 7: "липень", 8: "серпень",
    9: "вересень", 10: "жовтень", 11: "листопад", 12: "грудень",
}


@dataclass
class SettlementResult:
    """Результат розрахунку за один місячний файл.

    ``hours`` — погодинна таблиця з усіма проміжними величинами;
    ``daily`` — добові підсумки з ознакою перевищення порогу.
    Грошові підсумки — без ПДВ; ПДВ і сума з ПДВ рахуються властивостями.
    """

    hours: pd.DataFrame
    daily: pd.DataFrame
    settings: CalculationSettings
    source_name: str = ""
    warnings: list[str] = field(default_factory=list)

    # --- період -----------------------------------------------------------
    @property
    def period_start(self) -> date:
        return self.hours["date"].min()

    @property
    def period_end(self) -> date:
        return self.hours["date"].max()

    @property
    def month_label(self) -> str:
        """Назва періоду у вигляді «липень 2026»."""
        d = self.period_start
        return f"{UKR_MONTHS.get(d.month, d.month)} {d.year}"

    @property
    def period_key(self) -> str:
        """Машинний ключ періоду, напр. ``2026-07``."""
        d = self.period_start
        return f"{d.year:04d}-{d.month:02d}"

    # --- гроші ------------------------------------------------------------
    @property
    def total_net(self) -> float:
        """Загальний платіж за небаланси за місяць без ПДВ, грн."""
        return float(self.daily["cieq"].sum())

    @property
    def vat(self) -> float:
        return self.total_net * self.settings.vat_rate

    @property
    def total_gross(self) -> float:
        return self.total_net + self.vat

    # --- обсяги -----------------------------------------------------------
    @property
    def total_forecast_mwh(self) -> float:
        return float(self.hours["w_pr"].sum())

    @property
    def total_actual_mwh(self) -> float:
        return float(self.hours["w_f"].sum())

    @property
    def total_deviation_mwh(self) -> float:
        """Сальдо власного відхилення (з дельтами) за місяць."""
        return float(self.hours["dev"].sum())

    @property
    def total_abs_deviation_mwh(self) -> float:
        return float(self.hours["dev"].abs().sum())

    # --- аналітика --------------------------------------------------------
    @property
    def alert_days(self) -> pd.DataFrame:
        """Доби, платіж за які перевищує поріг."""
        return self.daily[self.daily["exceeds_threshold"]]

    @property
    def billable_hours(self) -> int:
        """Кількість годин, за які нарахований платіж."""
        return int((self.hours["cieq"] > 0).sum())

    @property
    def hours_total(self) -> int:
        return int(len(self.hours))

    @property
    def avg_cost_per_mwh(self) -> float:
        """Середня питома вартість небалансу, грн/МВт·год врахованого відхилення."""
        base = float(self.hours.loc[self.hours["cieq"] > 0, "w_alpha"].abs().sum())
        return self.total_net / base if base else 0.0
