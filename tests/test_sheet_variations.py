"""Тести змінного складу аркушів у місячному файлі ГП.

Кількість аркушів залежить від того, чи були команди ОСП у місяці: у
перевіреному наборі з 31 файлу трапляються 13, 14, 15 і 16 аркушів. Парсер,
який жорстко вимагає повний склад, відкидає саме ті місяці, де команд не
було, — див. docs/gp_file_format_variations.md.

Найнебезпечніший випадок — окремий аркуш ``ΔΣS``: файл при цьому має повний
вигляд і парсер його приймає, просто бере неповну дельту групи й тихо дає
інший рахунок.
"""

from __future__ import annotations

import io

import pytest
from openpyxl import Workbook

from imbalance_calc.dataio import load_monthly_file, validate_frame
from imbalance_calc.dataio.schema import (
    HOURS_PER_DAY,
    OPTIONAL_SHEETS,
    REQUIRED_SHEETS,
    SHEET_COLUMNS,
)
from imbalance_calc.exceptions import ValidationError

from .conftest import DAYS


def _workbook(values, skip=(), extra=None) -> io.BytesIO:
    """Скласти файл ГП без аркушів ``skip`` і з додатковими ``extra``."""
    wb = Workbook()
    wb.remove(wb.active)
    sheets = {n: c for n, c in SHEET_COLUMNS.items() if n not in skip and c in values}
    sheets.update(extra or {})
    for name, column in sheets.items():
        ws = wb.create_sheet(name[:31])
        ws.append(["Доба", "Зона"] + [f"{h} год" for h in range(1, HOURS_PER_DAY + 1)])
        for index, day in enumerate(DAYS):
            ws.append([day.strftime("%d.%m.%Y"), "IPS"] + list(values[column][index]))
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


@pytest.mark.parametrize("sheet", sorted(OPTIONAL_SHEETS))
def test_missing_optional_sheet_means_zero_delta(base_values, sheet):
    """Немає аркуша команд ОСП — дельта нульова, а не помилка читання."""
    frame = load_monthly_file(_workbook(base_values, skip={sheet}))
    column = OPTIONAL_SHEETS[sheet]
    if column == "d_sum_s":
        pytest.skip("ΔΣS не є окремою колонкою результату")
    assert (frame[column] == 0.0).all()
    assert validate_frame(frame) == []


def test_file_without_any_delta_sheets_loads(base_values):
    """13 аркушів: у місяці не було команд ОСП взагалі (грудень 2024 і 2025)."""
    frame = load_monthly_file(_workbook(base_values, skip=set(OPTIONAL_SHEETS)))
    assert (frame["d_w"] == 0.0).all()
    assert (frame["d_sum_w"] == 0.0).all()
    assert validate_frame(frame) == []


@pytest.mark.parametrize("sheet", sorted(REQUIRED_SHEETS))
def test_missing_required_sheet_still_raises(base_values, sheet):
    """Відсутність факту, прогнозу чи цін — це справді поламаний файл."""
    with pytest.raises(ValidationError, match="бракує аркушів"):
        load_monthly_file(_workbook(base_values, skip={sheet}))


def test_group_delta_sums_both_sheets(base_values):
    """ΔΣS додається до ΔΣW: інакше дельта групи неповна й рахунок інший."""
    hours = HOURS_PER_DAY
    base_values["d_sum_w"] = [[1.5] * hours for _ in DAYS]
    base_values["d_sum_s"] = [[0.25] * hours for _ in DAYS]
    # Контрольне співвідношення тримається на повній дельті групи
    base_values["w_sum_delta"] = [
        [base_values["w_sum"][d][h] + 1.75 for h in range(hours)] for d in range(len(DAYS))
    ]
    base_values["sum_w_sn_delta"] = [
        [base_values["w_sum_delta"][d][h] - base_values["sum_w_sp_delta"][d][h]
         for h in range(hours)]
        for d in range(len(DAYS))
    ]

    frame = load_monthly_file(_workbook(base_values))
    assert (frame["d_sum_w"] == 1.75).all()
    assert "d_sum_s" not in frame.columns
    assert validate_frame(frame) == []


def test_group_delta_without_extra_sheet_is_unchanged(base_values):
    """Коли ΔΣS немає, ΔΣW береться як є."""
    base_values["d_sum_w"] = [[1.75] * HOURS_PER_DAY for _ in DAYS]
    base_values["w_sum_delta"] = [
        [base_values["w_sum"][d][h] + 1.75 for h in range(HOURS_PER_DAY)]
        for d in range(len(DAYS))
    ]
    base_values["sum_w_sn_delta"] = [
        [base_values["w_sum_delta"][d][h] - base_values["sum_w_sp_delta"][d][h]
         for h in range(HOURS_PER_DAY)]
        for d in range(len(DAYS))
    ]
    frame = load_monthly_file(_workbook(base_values, skip={"ΔΣS"}))
    assert (frame["d_sum_w"] == 1.75).all()
