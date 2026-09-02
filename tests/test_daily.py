"""Тести добової агрегації та порогу для аналізу доби."""

from __future__ import annotations

import pandas as pd
import pytest

from imbalance_calc.config import CalculationSettings
from imbalance_calc.core import build_daily, calculate_settlement, filter_alert_days


def _daily(payments: list[float]) -> pd.DataFrame:
    """Штучна добова таблиця з заданими платежами."""
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-07-01", periods=len(payments)).date,
            "cieq": payments,
        }
    )


def test_one_row_per_day(frame):
    result = calculate_settlement(frame)
    assert len(result.daily) == frame["date"].nunique()


def test_daily_sum_matches_hours(frame):
    result = calculate_settlement(frame)
    for row in result.daily.itertuples(index=False):
        hours = result.hours[result.hours["date"] == row.date]
        assert row.cieq == pytest.approx(hours["cieq"].sum())


def test_threshold_is_exclusive():
    """Доба рівно з 10 000 грн не потрапляє у вибірку — порівняння строге."""
    daily = _daily([9_999.99, 10_000.0, 10_000.01])
    alerts = filter_alert_days(daily, 10_000.0)
    assert list(alerts["cieq"]) == [10_000.01]


def test_days_above_threshold_are_flagged(frame):
    result = calculate_settlement(frame, CalculationSettings(daily_threshold_uah=0.0))
    assert result.alert_days.equals(result.daily[result.daily["cieq"] > 0])


def test_high_threshold_leaves_no_alerts(frame):
    result = calculate_settlement(frame, CalculationSettings(daily_threshold_uah=1e12))
    assert result.alert_days.empty


def test_shares_sum_to_hundred(frame):
    result = calculate_settlement(frame)
    assert result.daily["share_pct"].sum() == pytest.approx(100.0)


def test_build_daily_counts_billed_hours(frame):
    result = calculate_settlement(frame)
    daily = build_daily(result.hours, 10_000.0)
    assert daily["hours_billed"].sum() == (result.hours["cieq"] > 0).sum()


def test_default_threshold_is_one_thousand():
    """Значення за замовчуванням винесене в config і має лишатися явним."""
    from imbalance_calc.config import DAILY_ALERT_THRESHOLD_UAH

    assert DAILY_ALERT_THRESHOLD_UAH == 1000.0
    assert CalculationSettings().daily_threshold_uah == 1000.0
