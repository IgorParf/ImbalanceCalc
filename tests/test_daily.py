"""Тести добового аналізу та порогу 10 000 грн."""

import pytest


@pytest.mark.skip(reason="не реалізовано")
def test_days_above_threshold_are_flagged(sample_day):
    ...


@pytest.mark.skip(reason="не реалізовано")
def test_threshold_is_exclusive(sample_day):
    """Доба рівно з 10 000 грн не має потрапляти у вибірку."""
    ...
