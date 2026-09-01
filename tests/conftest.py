"""Спільні фікстури: синтетичний файл ГП того самого формату, що й реальний."""

from __future__ import annotations

import io
from datetime import date

import pandas as pd
import pytest
from openpyxl import Workbook

from imbalance_calc.dataio.schema import HOURS_PER_DAY, SHEET_COLUMNS

#: Дві доби по 24 години — достатньо, щоб перевірити добову агрегацію.
DAYS = [date(2026, 7, 1), date(2026, 7, 2)]


def _base_values() -> dict[str, list[list[float]]]:
    """Погодинні значення для кожної колонки: список діб, у добі — 24 години."""
    hours = HOURS_PER_DAY

    def const(value: float) -> list[list[float]]:
        return [[value] * hours for _ in DAYS]

    values: dict[str, list[list[float]]] = {
        "w_pr": const(10.0),
        "w_f": const(9.0),
        "d_w": const(0.0),
        "imsp": const(3000.0),
        "p_dam": const(2000.0),
        "sum_w_sn_delta": const(-100.0),
        "sum_w_sp_delta": const(40.0),
        "sum_w_sn": const(-100.0),
        "sum_w_sp": const(40.0),
        "d_sum_w": const(0.0),
        "ieq_gb": const(-50.0),
    }
    # Похідні величини — щоб контрольні співвідношення сходилися
    values["w_s"] = [
        [values["w_f"][d][h] - values["w_pr"][d][h] for h in range(hours)]
        for d in range(len(DAYS))
    ]
    values["w_s_delta"] = [
        [values["w_s"][d][h] + values["d_w"][d][h] for h in range(hours)]
        for d in range(len(DAYS))
    ]
    values["w_sum"] = [
        [values["sum_w_sn"][d][h] + values["sum_w_sp"][d][h] for h in range(hours)]
        for d in range(len(DAYS))
    ]
    values["w_sum_delta"] = [
        [values["sum_w_sn_delta"][d][h] + values["sum_w_sp_delta"][d][h] for h in range(hours)]
        for d in range(len(DAYS))
    ]
    return values


def make_workbook(values: dict[str, list[list[float]]] | None = None) -> io.BytesIO:
    """Скласти xlsx у пам'яті зі структурою місячного файлу ГП."""
    values = values or _base_values()
    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, column in SHEET_COLUMNS.items():
        # Excel обрізає назви аркушів до 31 символу — відтворюємо це
        ws = wb.create_sheet(sheet_name[:31])
        ws.append(["Доба", "Зона"] + [f"{h} год" for h in range(1, HOURS_PER_DAY + 1)])
        for index, day in enumerate(DAYS):
            ws.append([day.strftime("%d.%m.%Y"), "IPS"] + list(values[column][index]))
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


@pytest.fixture
def base_values() -> dict[str, list[list[float]]]:
    return _base_values()


@pytest.fixture
def workbook_bytes() -> io.BytesIO:
    return make_workbook()


@pytest.fixture
def curtailed_frame() -> pd.DataFrame:
    """Дві доби, у першій — три години з обмеженнями ОСП різної глибини."""
    from imbalance_calc.dataio import load_monthly_file

    values = _base_values()
    # (година, факт, ΔW): 0,5 год + 0,25 год + 1,0 год = 1,75 год обмежень
    for hour, actual, curtailed in ((9, 5.0, 5.0), (10, 9.0, 3.0), (11, 0.0, 8.0)):
        values["w_f"][0][hour - 1] = actual
        values["d_w"][0][hour - 1] = curtailed
        values["w_s"][0][hour - 1] = actual - values["w_pr"][0][hour - 1]
        values["w_s_delta"][0][hour - 1] = values["w_s"][0][hour - 1] + curtailed
    return load_monthly_file(make_workbook(values))


@pytest.fixture
def frame(workbook_bytes) -> pd.DataFrame:
    from imbalance_calc.dataio import load_monthly_file

    return load_monthly_file(workbook_bytes)
