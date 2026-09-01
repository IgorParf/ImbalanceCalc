"""Добові підсумки та відбір діб із платежем понад поріг."""

from __future__ import annotations

import pandas as pd

from ..config import DAILY_ALERT_THRESHOLD_UAH


def build_daily(
    hours: pd.DataFrame,
    threshold_uah: float = DAILY_ALERT_THRESHOLD_UAH,
) -> pd.DataFrame:
    """Згрупувати погодинний розрахунок по добах.

    Повертає таблицю з колонками: ``date``, обсяги, ``cieq`` (платіж за добу
    без ПДВ), кількість тарифікованих годин, максимальний погодинний платіж,
    частка доби у місячному платежі та ознака перевищення порогу.
    """
    grouped = hours.groupby("date", as_index=False).agg(
        w_pr=("w_pr", "sum"),
        w_f=("w_f", "sum"),
        d_w=("d_w", "sum"),
        dev=("dev", "sum"),
        w_alpha=("w_alpha", "sum"),
        cieq=("cieq", "sum"),
        max_hour_cieq=("cieq", "max"),
        curtailed_mwh=("curtailed_mwh", "sum"),
        curtail_hours=("curtail_hours", "sum"),
    )
    grouped["abs_dev"] = hours.groupby("date")["dev"].apply(lambda s: s.abs().sum()).to_numpy()
    grouped["hours_billed"] = (
        hours.assign(_paid=hours["cieq"] > 0).groupby("date")["_paid"].sum().to_numpy()
    )
    grouped["curtailed_periods"] = (
        hours.assign(_cut=hours["d_w"] > 0).groupby("date")["_cut"].sum().to_numpy()
    )
    grouped["exceeds_threshold"] = grouped["cieq"] > threshold_uah

    total = grouped["cieq"].sum()
    grouped["share_pct"] = grouped["cieq"] / total * 100.0 if total else 0.0
    return grouped


def filter_alert_days(
    daily: pd.DataFrame,
    threshold_uah: float = DAILY_ALERT_THRESHOLD_UAH,
) -> pd.DataFrame:
    """Доби, платіж за які перевищує поріг (за замовчуванням 10 000 грн)."""
    return daily[daily["cieq"] > threshold_uah].sort_values("cieq", ascending=False)


def worst_hours(hours: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Години з найбільшим платежем — для аналізу причин."""
    columns = [
        "date", "hour", "w_pr", "w_f", "dev", "dev_pct",
        "w_alpha", "p_dam", "imsp", "w_group", "scenario", "cieq",
    ]
    return hours.nlargest(limit, "cieq")[columns]
