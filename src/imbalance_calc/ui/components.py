"""Спільні елементи інтерфейсу Streamlit."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from ..config import (
    DAILY_ALERT_THRESHOLD_UAH,
    DEFAULT_ALPHA,
    DEFAULT_K_E,
    DEFAULT_K_IM,
    DEFAULT_VAT_RATE,
    CalculationSettings,
)
from ..core import calculate_from_file
from ..models import SettlementResult
from ..reporting import money, volume

#: Ключі у ``st.session_state``.
KEY_RESULT = "result"
KEY_COMPARE = "compare_result"
KEY_PDF = "pdf_report"
KEY_XLSX = "xlsx_report"
KEY_SIGNATURE = "result_signature"


def reset_reports() -> None:
    """Скинути раніше сформовані звіти (файл або параметри змінилися)."""
    st.session_state.pop(KEY_PDF, None)
    st.session_state.pop(KEY_XLSX, None)


def bootstrap_path() -> None:
    """Додати ``src`` у ``sys.path`` — потрібно для запуску сторінок Streamlit."""
    root = Path(__file__).resolve().parents[3]
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))


def page_config(title: str) -> None:
    st.set_page_config(page_title=title, page_icon="⚡", layout="wide")


def settings_sidebar(key_prefix: str = "main") -> CalculationSettings:
    """Панель параметрів розрахунку; значення за замовчуванням — з config."""
    with st.sidebar:
        st.header("Параметри розрахунку")
        st.caption(
            "Величини, яких немає у файлі ГП. Значення за замовчуванням треба "
            "звіряти з договором і чинною редакцією Закону."
        )
        k_e = st.number_input(
            "K_e — допустиме відхилення, %",
            min_value=0.0, max_value=100.0, value=DEFAULT_K_E, step=1.0,
            key=f"{key_prefix}_k_e",
            help="Години, у яких відносне відхилення не перевищує K_e, не тарифікуються.",
        )
        alpha = st.number_input(
            "α — частка відшкодування, %",
            min_value=0.0, max_value=100.0, value=DEFAULT_ALPHA, step=5.0,
            key=f"{key_prefix}_alpha",
        )
        k_im = st.number_input(
            "K_im — коефіцієнт ціни небалансу",
            min_value=0.0, max_value=1.0, value=DEFAULT_K_IM, step=0.01, format="%.2f",
            key=f"{key_prefix}_k_im",
        )
        vat = st.number_input(
            "Ставка ПДВ, %",
            min_value=0.0, max_value=100.0, value=DEFAULT_VAT_RATE * 100, step=1.0,
            key=f"{key_prefix}_vat",
        )
        threshold = st.number_input(
            "Поріг для аналізу доби, грн",
            min_value=0.0, value=DAILY_ALERT_THRESHOLD_UAH, step=1000.0,
            key=f"{key_prefix}_threshold",
            help="Доби, платіж за які перевищує поріг, аналізуються окремо.",
        )
        st.divider()
        st.caption("Методика: docs/METHODOLOGY.md")
    return CalculationSettings(
        k_e=k_e, alpha=alpha, k_im=k_im,
        vat_rate=vat / 100.0, daily_threshold_uah=threshold,
    )


@st.cache_data(show_spinner=False)
def _cached_result(
    payload: bytes, name: str, settings: CalculationSettings
) -> SettlementResult:
    return calculate_from_file(io.BytesIO(payload), settings, source_name=name)


def run_calculation(uploaded, settings: CalculationSettings) -> SettlementResult:
    """Виконати розрахунок для завантаженого файлу (з кешуванням)."""
    return _cached_result(uploaded.getvalue(), uploaded.name, settings)


def render_totals(result: SettlementResult) -> None:
    """Картки з місячними підсумками."""
    columns = st.columns(4)
    columns[0].metric("Прогноз, МВт·год", volume(result.total_forecast_mwh))
    columns[1].metric("Факт, МВт·год", volume(result.total_actual_mwh))
    columns[2].metric("Сальдо відхилення, МВт·год", volume(result.total_deviation_mwh))
    columns[3].metric(
        "Годин з платежем", f"{result.billable_hours} з {result.hours_total}"
    )


def render_payment_block(result: SettlementResult) -> None:
    """Підсумковий блок: платіж, ПДВ, всього з ПДВ."""
    rate = result.settings.vat_rate * 100
    st.markdown("#### Платіж за небаланси електричної енергії")
    columns = st.columns(3)
    columns[0].metric("Платіж без ПДВ, грн", money(result.total_net))
    columns[1].metric(f"ПДВ {rate:g} %, грн", money(result.vat))
    columns[2].metric("Всього з ПДВ, грн", money(result.total_gross))


def daily_chart(result: SettlementResult) -> alt.Chart:
    """Стовпчикова діаграма платежів по добах із лінією порогу."""
    frame = result.daily.copy()
    frame["Доба"] = pd.to_datetime(frame["date"])
    frame["Платіж, грн"] = frame["cieq"]
    frame["Понад поріг"] = frame["exceeds_threshold"].map({True: "так", False: "ні"})

    bars = (
        alt.Chart(frame)
        .mark_bar()
        .encode(
            x=alt.X("Доба:T", axis=alt.Axis(format="%d.%m", labelAngle=-45, tickCount="day")),
            y=alt.Y("Платіж, грн:Q"),
            color=alt.Color(
                "Понад поріг:N",
                scale=alt.Scale(domain=["ні", "так"], range=["#5b8db8", "#c0392b"]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("Доба:T", format="%d.%m.%Y"),
                alt.Tooltip("Платіж, грн:Q", format=",.2f"),
                alt.Tooltip("hours_billed:Q", title="Годин з платежем"),
                alt.Tooltip("dev:Q", title="Відхилення, МВт·год", format=",.3f"),
            ],
        )
    )
    rule = (
        alt.Chart(pd.DataFrame({"y": [result.settings.daily_threshold_uah]}))
        .mark_rule(color="#c0392b", strokeDash=[6, 4])
        .encode(y="y:Q")
    )
    return (bars + rule).properties(height=280)


def render_warnings(result: SettlementResult) -> None:
    """Показати зауваження валідації, якщо вони є."""
    if not result.warnings:
        return
    with st.expander(f"Зауваження до вхідних даних ({len(result.warnings)})", expanded=False):
        for warning in result.warnings:
            st.warning(warning)


def require_result(key: str = KEY_RESULT) -> SettlementResult | None:
    """Отримати результат із сесії або показати підказку."""
    result = st.session_state.get(key)
    if result is None:
        st.info("Спочатку завантажте файл з даними на сторінці «Розрахунок».")
    return result
