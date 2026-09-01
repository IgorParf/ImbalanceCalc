"""Спільні фікстури для тестів."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from imbalance_calc.models import PeriodRecord


@pytest.fixture
def sample_day() -> list[PeriodRecord]:
    """Одна доба з 24 годин: план 10 МВт·год, факт із невеликими відхиленнями."""
    start = datetime(2025, 1, 1)
    return [
        PeriodRecord(
            timestamp=start + timedelta(hours=h),
            planned_mwh=Decimal("10"),
            actual_mwh=Decimal("10") + Decimal(h % 3) - Decimal("1"),
            price_uah_mwh=Decimal("2500"),
        )
        for h in range(24)
    ]
