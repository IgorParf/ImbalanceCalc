"""Перевірка повноти та внутрішньої узгодженості вхідних даних.

Перевіряються контрольні співвідношення з docs/METHODOLOGY.md, розділ 8:
файл ГП містить і вихідні величини, і похідні від них, тому розбіжність
означає пошкоджений або відредагований вручну файл.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import HOURS_PER_DAY, REQUIRED_COLUMNS

#: Допуск при звірці контрольних співвідношень, МВт·год.
TOLERANCE = 1e-6


def _mismatch_count(left: pd.Series, right: pd.Series) -> int:
    return int((np.abs(left - right) > TOLERANCE).sum())


def validate_frame(df: pd.DataFrame) -> list[str]:
    """Перевірити погодинну таблицю та повернути список попереджень."""
    warnings: list[str] = []

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        warnings.append("Відсутні колонки: " + ", ".join(missing))
        return warnings

    # Повнота календаря
    per_day = df.groupby("date")["hour"].count()
    short_days = per_day[per_day != HOURS_PER_DAY]
    for day, count in short_days.items():
        warnings.append(f"Доба {day:%d.%m.%Y}: {count} годин замість {HOURS_PER_DAY}")

    days = pd.to_datetime(sorted(df["date"].unique()))
    if len(days) > 1:
        gaps = pd.Series(days).diff().dropna()
        if (gaps > pd.Timedelta(days=1)).any():
            warnings.append("У переліку діб є пропуски — перевірте повноту файлу")
        if days[0].month != days[-1].month:
            warnings.append("Файл охоплює більше одного календарного місяця")

    if df.duplicated(subset=["date", "hour"]).any():
        warnings.append("У файлі є дублікати пар «доба + година»")

    # Пропущені значення
    nulls = df[list(REQUIRED_COLUMNS)].isna().sum()
    for column, count in nulls[nulls > 0].items():
        warnings.append(f"Колонка «{column}»: {count} порожніх значень")

    # Контрольні співвідношення
    checks = {
        "Фактичне відхилення без дельт ≠ Факт − Прогноз": _mismatch_count(
            df["w_s"], df["w_f"] - df["w_pr"]
        ),
        "Фактичне відхилення ≠ (без дельт) + ΔW": _mismatch_count(
            df["w_s_delta"], df["w_s"] + df["d_w"]
        ),
        "Сальдо групи ≠ W sn + W sp": _mismatch_count(
            df["w_sum_delta"], df["sum_w_sn_delta"] + df["sum_w_sp_delta"]
        ),
        "Сальдо групи без дельт ≠ W sn + W sp (без дельт)": _mismatch_count(
            df["w_sum"], df["sum_w_sn"] + df["sum_w_sp"]
        ),
        "Сальдо групи ≠ (без дельт) + ΔΣW": _mismatch_count(
            df["w_sum_delta"], df["w_sum"] + df["d_sum_w"]
        ),
    }
    for label, count in checks.items():
        if count:
            warnings.append(f"Контрольне співвідношення не збігається у {count} год.: {label}")

    # Ціни
    if (df["imsp"] < 0).any() or (df["p_dam"] < 0).any():
        warnings.append("У файлі є від'ємні ціни — перевірте вхідні дані")

    return warnings
