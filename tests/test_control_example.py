"""Звірка розрахунку з реально виставленим рахунком.

Реальні дані комерційного обліку та суми рахунків у репозиторій не потрапляють:
тест бере їх з локального файлу ``data/input/control.json``, який не
відстежується git. Якщо файлу немає — тест пропускається.

Формат ``data/input/control.json``::

    {
      "file": "62W000000000000X липень 2026.xlsx",
      "total_net_uah": 123456.78,
      "k_e": 5.0,
      "alpha": 100.0,
      "k_im": 0.05,
      "hours": 744,
      "period_key": "2026-07"
    }

Обов'язкові поля — ``file`` і ``total_net_uah``; решта необов'язкові.
Створити заготовку: ``python scripts/make_control_config.py``.
"""

from __future__ import annotations

import json

import pytest

from imbalance_calc.config import INPUT_DIR, CalculationSettings
from imbalance_calc.core import calculate_from_file

CONTROL_CONFIG = INPUT_DIR / "control.json"


def _load_config() -> dict | None:
    if not CONTROL_CONFIG.exists():
        return None
    try:
        config = json.loads(CONTROL_CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        pytest.fail(f"{CONTROL_CONFIG} містить некоректний JSON: {error}")
    if not {"file", "total_net_uah"} <= set(config):
        pytest.fail(f"{CONTROL_CONFIG}: обов'язкові поля — file та total_net_uah")
    return config


CONFIG = _load_config()

pytestmark = pytest.mark.skipif(
    CONFIG is None,
    reason=f"немає {CONTROL_CONFIG.name} у data/input/ — звірка з рахунком пропущена",
)


@pytest.fixture(scope="module")
def settings() -> CalculationSettings:
    defaults = CalculationSettings()
    return CalculationSettings(
        k_e=CONFIG.get("k_e", defaults.k_e),
        alpha=CONFIG.get("alpha", defaults.alpha),
        k_im=CONFIG.get("k_im", defaults.k_im),
    )


@pytest.fixture(scope="module")
def control_result(settings):
    path = INPUT_DIR / CONFIG["file"]
    if not path.exists():
        pytest.skip(f"немає файлу {path.name}, вказаного у {CONTROL_CONFIG.name}")
    return calculate_from_file(path, settings)


def test_total_matches_invoice(control_result):
    """Розбіжність не більша за копійку — рахунок округлений до копійок."""
    assert control_result.total_net == pytest.approx(CONFIG["total_net_uah"], abs=0.01)


def test_file_passes_validation(control_result):
    assert control_result.warnings == []


def test_period_matches_config(control_result):
    if "period_key" in CONFIG:
        assert control_result.period_key == CONFIG["period_key"]
    if "hours" in CONFIG:
        assert control_result.hours_total == CONFIG["hours"]


def test_price_coefficient_is_load_bearing(control_result, settings):
    """K_im — найчутливіший параметр: з нулем підсумок помітно менший."""
    if settings.k_im == 0:
        pytest.skip("у конфігурації K_im = 0, порівнювати нема з чим")

    without = calculate_from_file(
        INPUT_DIR / CONFIG["file"],
        CalculationSettings(k_e=settings.k_e, alpha=settings.alpha, k_im=0.0),
    )
    assert without.total_net < control_result.total_net
