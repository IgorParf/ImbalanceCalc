"""Тести підсумкового розрахунку та ПДВ."""

from __future__ import annotations

import pytest

from imbalance_calc.config import CalculationSettings
from imbalance_calc.core import calculate_settlement, correction_payment


def test_total_equals_sum_of_days(frame):
    result = calculate_settlement(frame)
    assert result.total_net == pytest.approx(result.daily["cieq"].sum())
    assert result.total_net == pytest.approx(result.hours["cieq"].sum())


def test_payment_is_never_negative(frame):
    result = calculate_settlement(frame)
    assert (result.hours["cieq"] >= 0).all()


def test_vat_is_added_on_top(frame):
    result = calculate_settlement(frame, CalculationSettings(vat_rate=0.20))
    assert result.vat == pytest.approx(result.total_net * 0.20)
    assert result.total_gross == pytest.approx(result.total_net * 1.20)


def test_alpha_scales_payment_linearly(frame):
    full = calculate_settlement(frame, CalculationSettings(alpha=100.0))
    half = calculate_settlement(frame, CalculationSettings(alpha=50.0))
    assert half.total_net == pytest.approx(full.total_net / 2)


def test_large_dead_zone_zeroes_payment(frame):
    # Відхилення у фікстурі — 10 %, тож K_e = 50 % прибирає всі години
    result = calculate_settlement(frame, CalculationSettings(k_e=50.0))
    assert result.total_net == 0.0
    assert result.billable_hours == 0


def test_period_label(frame):
    result = calculate_settlement(frame)
    assert result.month_label == "липень 2026"
    assert result.period_key == "2026-07"


def test_correction_payment_is_difference(frame):
    previous = calculate_settlement(frame, CalculationSettings(alpha=50.0))
    updated = calculate_settlement(frame, CalculationSettings(alpha=100.0))
    assert correction_payment(updated, previous) == pytest.approx(
        updated.total_net - previous.total_net
    )
