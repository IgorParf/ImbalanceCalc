"""Опис очікуваної структури вхідного файлу."""

from __future__ import annotations

#: Канонічні назви колонок, з якими працює розрахунок.
REQUIRED_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "planned_mwh",
    "actual_mwh",
)

OPTIONAL_COLUMNS: tuple[str, ...] = (
    "price_uah_mwh",
    "direction",
    "meter_point",
)

#: Можливі назви колонок у файлах постачальників -> канонічна назва.
COLUMN_ALIASES: dict[str, str] = {
    "дата": "timestamp",
    "дата/час": "timestamp",
    "датачас": "timestamp",
    "період": "timestamp",
    "година": "hour",
    "план": "planned_mwh",
    "плановий обсяг": "planned_mwh",
    "заявлений обсяг": "planned_mwh",
    "факт": "actual_mwh",
    "фактичний обсяг": "actual_mwh",
    "ціна": "price_uah_mwh",
    "ціна небалансу": "price_uah_mwh",
}
