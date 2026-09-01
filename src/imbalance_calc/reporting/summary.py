"""Підсумкові таблиці та форматування чисел для UI і звітів."""

from __future__ import annotations

import pandas as pd

from ..dataio.schema import COLUMN_TITLES
from ..models import SettlementResult


def money(value: float, digits: int = 2) -> str:
    """Форматувати гривні: 1 234 567,89."""
    text = f"{value:,.{digits}f}"
    return text.replace(",", " ").replace(".", ",")


def volume(value: float, digits: int = 3) -> str:
    """Форматувати обсяг у МВт·год."""
    return money(value, digits)


def totals_rows(result: SettlementResult) -> list[tuple[str, str]]:
    """Рядки підсумкової таблиці, включно з ПДВ."""
    rate = result.settings.vat_rate * 100
    return [
        ("Період", result.month_label),
        ("Прогнозний обсяг, МВт·год", volume(result.total_forecast_mwh)),
        ("Фактичний обсяг, МВт·год", volume(result.total_actual_mwh)),
        ("Сальдо відхилення, МВт·год", volume(result.total_deviation_mwh)),
        ("Сума відхилень за модулем, МВт·год", volume(result.total_abs_deviation_mwh)),
        ("Годин з платежем", f"{result.billable_hours} з {result.hours_total}"),
        ("Платіж за небаланси без ПДВ, грн", money(result.total_net)),
        (f"ПДВ {rate:g} %, грн", money(result.vat)),
        ("Всього з ПДВ, грн", money(result.total_gross)),
    ]


def daily_display(result: SettlementResult) -> pd.DataFrame:
    """Добова таблиця у вигляді для показу користувачу."""
    frame = result.daily.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%d.%m.%Y")
    frame = frame[
        [
            "date", "w_pr", "w_f", "dev", "w_alpha",
            "hours_billed", "max_hour_cieq", "cieq", "share_pct", "exceeds_threshold",
        ]
    ]
    return frame.rename(columns=COLUMN_TITLES)


def hourly_display(hours: pd.DataFrame) -> pd.DataFrame:
    """Погодинна таблиця у вигляді для показу користувачу."""
    frame = hours.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%d.%m.%Y")
    columns = [
        "date", "hour", "w_pr", "w_f", "d_w", "dev", "dev_pct", "w_alpha",
        "p_dam", "imsp", "w_group", "ieq_gb", "scenario", "cieq",
    ]
    return frame[columns].rename(columns=COLUMN_TITLES)


def summary_text(result: SettlementResult) -> str:
    """Короткий текстовий підсумок одним абзацом."""
    alerts = len(result.alert_days)
    threshold = money(result.settings.daily_threshold_uah, 0)
    return (
        f"{result.month_label}: платіж за небаланси {money(result.total_net)} грн без ПДВ, "
        f"ПДВ {money(result.vat)} грн, всього {money(result.total_gross)} грн. "
        f"Тарифікованих годин {result.billable_hours} з {result.hours_total}; "
        f"діб із платежем понад {threshold} грн — {alerts}."
    )


def compare(a: SettlementResult, b: SettlementResult) -> pd.DataFrame:
    """Порівняння двох місяців: значення, різниця, зміна у відсотках."""

    def rows(r: SettlementResult) -> dict[str, float]:
        return {
            "Прогноз, МВт·год": r.total_forecast_mwh,
            "Факт, МВт·год": r.total_actual_mwh,
            "Сальдо відхилення, МВт·год": r.total_deviation_mwh,
            "Відхилення за модулем, МВт·год": r.total_abs_deviation_mwh,
            "Годин з платежем": r.billable_hours,
            "Діб понад поріг": len(r.alert_days),
            "Платіж без ПДВ, грн": r.total_net,
            "ПДВ, грн": r.vat,
            "Всього з ПДВ, грн": r.total_gross,
            "Середня вартість, грн/МВт·год": r.avg_cost_per_mwh,
        }

    left, right = rows(a), rows(b)
    label_a, label_b = a.month_label, b.month_label
    if label_a == label_b:  # порівняння двох версій одного місяця
        label_a, label_b = f"{label_a} (1)", f"{label_b} (2)"
    frame = pd.DataFrame(
        {
            "Показник": list(left),
            label_a: list(left.values()),
            label_b: [right[k] for k in left],
        }
    )
    frame["Різниця"] = frame[label_b] - frame[label_a]
    base = frame[label_a].replace(0, pd.NA)
    frame["Зміна, %"] = (frame["Різниця"] / base * 100).astype(float).round(1)
    return frame


def daily_comparison(a: SettlementResult, b: SettlementResult) -> pd.DataFrame:
    """Порівняння двох місяців по номеру доби (1–31)."""
    left = a.daily.assign(day=pd.to_datetime(a.daily["date"]).dt.day)[["day", "cieq"]]
    right = b.daily.assign(day=pd.to_datetime(b.daily["date"]).dt.day)[["day", "cieq"]]
    label_a, label_b = a.month_label, b.month_label
    if label_a == label_b:
        label_a, label_b = f"{label_a} (1)", f"{label_b} (2)"
    merged = left.merge(right, on="day", how="outer", suffixes=("_a", "_b")).sort_values("day")
    return merged.rename(
        columns={"day": "День", "cieq_a": label_a, "cieq_b": label_b}
    ).fillna(0.0)
