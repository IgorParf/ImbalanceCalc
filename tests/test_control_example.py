"""Звірка з реально виставленим рахунком (розділ 12 docs/METHODOLOGY.md).

Тест виконується лише тоді, коли файл лежить у ``data/input/`` — реальні дані
комерційного обліку в репозиторій не потрапляють. Покладіть туди файл ГП,
і тест почне контролювати, що зміни в коді не зсувають підсумок.
"""

from __future__ import annotations

import pytest

from imbalance_calc.config import INPUT_DIR, CalculationSettings
from imbalance_calc.core import calculate_from_file

#: Файл і сума з рахунку за липень 2026, без ПДВ.
CONTROL_FILE = INPUT_DIR / "62W663740852221O липень 2026.xlsx"
CONTROL_TOTAL_UAH = 637_464.21

#: Параметри, за яких досягнуто збіг.
CONTROL_SETTINGS = CalculationSettings(k_e=5.0, alpha=100.0, k_im=0.05)

pytestmark = pytest.mark.skipif(
    not CONTROL_FILE.exists(),
    reason=f"немає контрольного файлу {CONTROL_FILE.name} у data/input/",
)


@pytest.fixture(scope="module")
def control_result():
    return calculate_from_file(CONTROL_FILE, CONTROL_SETTINGS)


def test_total_matches_invoice(control_result):
    """Розбіжність не більша за копійку — рахунок округлений до копійок."""
    assert control_result.total_net == pytest.approx(CONTROL_TOTAL_UAH, abs=0.01)


def test_file_passes_validation(control_result):
    assert control_result.warnings == []


def test_period_is_july_2026(control_result):
    assert control_result.period_key == "2026-07"
    assert control_result.hours_total == 744


def test_zero_price_coefficient_underestimates(control_result):
    """K_im = 0 дає помітний недобір — саме на цьому параметрі ловиться помилка."""
    without = calculate_from_file(
        CONTROL_FILE, CalculationSettings(k_e=5.0, alpha=100.0, k_im=0.0)
    )
    assert without.total_net < control_result.total_net
    assert without.total_net == pytest.approx(596_625.35, abs=0.01)
