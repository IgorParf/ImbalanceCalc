"""Тести читання місячного файлу ГП."""

from __future__ import annotations

import io
from datetime import date

import pytest
from openpyxl import Workbook

from imbalance_calc.dataio import load_monthly_file, validate_frame
from imbalance_calc.dataio.loaders import _match_sheet, guess_period_label
from imbalance_calc.dataio.schema import HOURS_PER_DAY, REQUIRED_COLUMNS
from imbalance_calc.exceptions import ValidationError


def test_loads_all_columns(frame):
    assert set(REQUIRED_COLUMNS).issubset(frame.columns)
    assert len(frame) == 2 * HOURS_PER_DAY
    assert frame["date"].min() == date(2026, 7, 1)
    assert frame["hour"].max() == HOURS_PER_DAY


def test_truncated_sheet_name_maps_to_delta_free_variant():
    """Excel обрізає назву до 31 символу — вона має відповідати «без дельт»."""
    assert _match_sheet("Сальдовий обсяг небалансу без д") == "w_sum"
    assert _match_sheet("Сальдовий обсяг небалансу") == "w_sum_delta"
    assert _match_sheet("W sn") == "sum_w_sn_delta"
    assert _match_sheet("W sn без дельт") == "sum_w_sn"


def test_unknown_sheet_is_ignored():
    assert _match_sheet("Якийсь службовий аркуш") is None


def test_missing_sheets_raise():
    wb = Workbook()
    wb.active.title = "Остаточний прогноз"
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    with pytest.raises(ValidationError, match="бракує аркушів"):
        load_monthly_file(buffer)


def test_valid_file_has_no_warnings(frame):
    assert validate_frame(frame) == []


def test_broken_control_relation_is_reported(frame):
    frame.loc[0, "w_s"] = frame.loc[0, "w_s"] + 1.0
    warnings = validate_frame(frame)
    assert any("Факт − Прогноз" in w for w in warnings)


def test_guess_period_label():
    assert guess_period_label("62W663740852221O липень 2026 (1).xlsx") == "липень 2026"
    assert guess_period_label("report.xlsx") == ""
