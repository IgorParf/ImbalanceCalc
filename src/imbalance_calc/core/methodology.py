"""Погодинний розрахунок за Порядком (Додаток 2 до Типового договору).

Реалізовані глави 1–3 Порядку; посилання на пункти — у коментарях.
Повний опис — docs/METHODOLOGY.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import CalculationSettings

#: Позначення сценаріїв вибору за п. 2.1.
SCENARIO_BASE = "SUM"
SCENARIO_DELTA = "SUMΔ"


def group_cost(
    w: pd.Series | np.ndarray,
    p_dam: pd.Series | np.ndarray,
    imsp: pd.Series | np.ndarray,
    k_im: float,
) -> np.ndarray:
    """Вартість сальдованого небалансу групи за годину, грн (пп. 1.3, 1.4).

    При надлишку (``w > 0``) група недоотримує різницю між ціною РДН і ціною
    небалансу; при дефіциті (``w < 0``) — доплачує понад ціну РДН.
    """
    w = np.asarray(w, dtype=float)
    p_dam = np.asarray(p_dam, dtype=float)
    imsp = np.asarray(imsp, dtype=float)

    surplus = w * (p_dam - np.minimum(p_dam, imsp) * (1 - k_im))
    deficit = np.abs(w) * (np.maximum(p_dam, imsp) * (1 + k_im) - p_dam)
    return np.where(w > 0, surplus, np.where(w < 0, deficit, 0.0))


def curtailment_duration(w_f: pd.Series, d_w: pd.Series) -> np.ndarray:
    """Еквівалентна тривалість обмеження в межах години, год.

    Файл ГП подає обсяг невідпущеної енергії, а не час дії команди ОСП. Якщо
    обмеження діяло частину години, ``ΔW`` менший за потенційний виробіток —
    відношення ``ΔW / (W^F + ΔW)`` і дає частку години під обмеженням.
    Наприклад, ΔW = 4,120 при фактичних 1,384 МВт·год означає потенціал
    5,504 МВт·год і 0,749 год = 45 хв обмеження.

    Величина суто інформативна: у розрахунок платежу вона не входить.
    """
    actual = np.asarray(w_f, dtype=float)
    curtailed = np.asarray(d_w, dtype=float)
    potential = actual + curtailed
    with np.errstate(divide="ignore", invalid="ignore"):
        share = np.where(potential > 0, np.minimum(1.0, curtailed / potential), 1.0)
    return np.where(curtailed > 0, share, 0.0)


def accounted_deviation(
    w_pr: pd.Series,
    w_f: pd.Series,
    d_w: pd.Series,
    settings: CalculationSettings,
) -> tuple[np.ndarray, np.ndarray]:
    """Враховане відхилення Учасника W^alpha та ознака перевищення K_e (п. 3.1).

    Відхилення завжди береться з дельтами (``W^F − W^PR + ΔW + ΔS``), незалежно
    від того, який сценарій буде обрано за п. 2.1. Якщо прогноз нульовий,
    перевірка на K_e не застосовується.
    """
    dev = np.asarray(w_f - w_pr + d_w, dtype=float)
    pr = np.asarray(w_pr, dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        dev_pct = np.where(pr != 0, np.abs(dev) / np.abs(pr) * 100.0, np.inf)

    billable = (pr == 0) | (dev_pct > settings.k_e)
    w_alpha = np.where(billable, dev * settings.alpha / 100.0, 0.0)
    return w_alpha, billable


def participant_share(
    w_alpha: np.ndarray,
    w_group: np.ndarray,
    sum_sn: np.ndarray,
    sum_sp: np.ndarray,
    ieq_gb: np.ndarray,
    p_dam: np.ndarray,
    imsp: np.ndarray,
    k_im: float,
) -> np.ndarray:
    """Частка вартості врегулювання, що відшкодовується Учасником (п. 3.2).

    Платіж нараховується лише коли збігаються три знаки: сальдо групи,
    власне враховане відхилення та небаланс самого Гарантованого покупця.
    """
    deficit_price = np.maximum(p_dam, imsp) * (1 + k_im) - p_dam
    surplus_price = p_dam - np.minimum(p_dam, imsp) * (1 - k_im)

    with np.errstate(divide="ignore", invalid="ignore"):
        deficit = np.abs(np.where(sum_sn != 0, w_alpha / sum_sn, 0.0) * w_group) * deficit_price
        surplus = np.where(sum_sp != 0, w_alpha / sum_sp, 0.0) * w_group * surplus_price

    is_deficit = (w_group < 0) & (w_alpha < 0) & (ieq_gb < 0) & (sum_sn != 0)
    is_surplus = (w_group > 0) & (w_alpha > 0) & (ieq_gb > 0) & (sum_sp != 0)

    result = np.where(is_deficit, deficit, np.where(is_surplus, surplus, 0.0))
    return np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)


def calculate_hourly(df: pd.DataFrame, settings: CalculationSettings) -> pd.DataFrame:
    """Виконати повний погодинний розрахунок і додати похідні колонки.

    Додаються: ``dev``, ``dev_pct``, ``w_alpha``, ``billable``,
    ``cieq_sum``, ``cieq_sum_delta``, ``scenario``, ``w_group``, ``cieq``.
    """
    out = df.copy()

    # Глава 1: вартість небалансу групи в обох сценаріях
    out["cieq_sum"] = group_cost(out["w_sum"], out["p_dam"], out["imsp"], settings.k_im)
    out["cieq_sum_delta"] = group_cost(
        out["w_sum_delta"], out["p_dam"], out["imsp"], settings.k_im
    )

    # Глава 2, п. 2.1: погодинний вибір дешевшого для групи сценарію
    use_base = out["cieq_sum"] <= out["cieq_sum_delta"]
    out["scenario"] = np.where(use_base, SCENARIO_BASE, SCENARIO_DELTA)
    out["w_group"] = np.where(use_base, out["w_sum"], out["w_sum_delta"])
    sum_sn = np.where(use_base, out["sum_w_sn"], out["sum_w_sn_delta"])
    sum_sp = np.where(use_base, out["sum_w_sp"], out["sum_w_sp_delta"])
    out["sum_sn_used"] = sum_sn
    out["sum_sp_used"] = sum_sp

    # Обмеження ОСП: обсяг та еквівалентна тривалість (для звітності, не для платежу)
    out["curtailed_mwh"] = out["d_w"].clip(lower=0.0)
    out["curtail_hours"] = curtailment_duration(out["w_f"], out["d_w"])

    # Глава 3, п. 3.1: враховане відхилення Учасника
    out["dev"] = out["w_f"] - out["w_pr"] + out["d_w"]
    with np.errstate(divide="ignore", invalid="ignore"):
        out["dev_pct"] = np.where(
            out["w_pr"] != 0, np.abs(out["dev"]) / np.abs(out["w_pr"]) * 100.0, np.nan
        )
    w_alpha, billable = accounted_deviation(out["w_pr"], out["w_f"], out["d_w"], settings)
    out["w_alpha"] = w_alpha
    out["billable"] = billable

    # Глава 3, п. 3.2: частка вартості, що відшкодовується Учасником
    out["cieq"] = participant_share(
        w_alpha=w_alpha,
        w_group=np.asarray(out["w_group"], dtype=float),
        sum_sn=np.asarray(sum_sn, dtype=float),
        sum_sp=np.asarray(sum_sp, dtype=float),
        ieq_gb=np.asarray(out["ieq_gb"], dtype=float),
        p_dam=np.asarray(out["p_dam"], dtype=float),
        imsp=np.asarray(out["imsp"], dtype=float),
        k_im=settings.k_im,
    )
    return out


def recalculate(df: pd.DataFrame, settings: CalculationSettings | None = None) -> pd.DataFrame:
    """Зручна обгортка над :func:`calculate_hourly` з параметрами за замовчуванням."""
    return calculate_hourly(df, settings or CalculationSettings())
