"""Багаторазові елементи інтерфейсу."""

from __future__ import annotations

from ..models import SettlementResult


def render_upload() -> object | None:
    """Блок завантаження файлу; повертає файловий об'єкт або ``None``."""
    raise NotImplementedError


def render_settings() -> object:
    """Блок налаштувань розрахунку (поріг, період, ПДВ)."""
    raise NotImplementedError


def render_totals(result: SettlementResult) -> None:
    """Картки з загальним платежем та обсягом небалансу."""
    raise NotImplementedError


def render_daily_table(result: SettlementResult) -> None:
    """Таблиця та графік по добах із підсвіткою діб понад поріг."""
    raise NotImplementedError


def render_alert_days(result: SettlementResult) -> None:
    """Окремий блок аналізу діб із платежем понад 10 000 грн."""
    raise NotImplementedError
