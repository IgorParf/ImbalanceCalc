"""Спільні елементи інтерфейсу Streamlit."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from .. import config, store
from ..config import (
    DAILY_ALERT_THRESHOLD_UAH,
    DEFAULT_ALPHA,
    DEFAULT_K_E,
    DEFAULT_K_IM,
    DEFAULT_VAT_RATE,
    CalculationSettings,
)
from ..core import calculate_settlement
from ..dataio import load_monthly_file, validate_frame
from ..models import SettlementResult
from ..reporting import duration, money, volume

#: Ключі у ``st.session_state``.
KEY_RESULT = "result"
KEY_PERIOD = "period_key"
KEY_COMPARE = "compare_result"
KEY_PDF = "pdf_report"
KEY_XLSX = "xlsx_report"
KEY_PDF_PATH = "pdf_report_path"
KEY_XLSX_PATH = "xlsx_report_path"
KEY_SIGNATURE = "result_signature"


def reset_reports() -> None:
    """Скинути раніше сформовані звіти (період або параметри змінилися)."""
    for key in (KEY_PDF, KEY_XLSX, KEY_PDF_PATH, KEY_XLSX_PATH):
        st.session_state.pop(key, None)


def bootstrap_path() -> None:
    """Додати ``src`` у ``sys.path`` — потрібно для окремого запуску сторінки."""
    root = Path(__file__).resolve().parents[3]
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))


# ------------------------------------------------------------------ дані ----


def _cache_token(period_key: str) -> float:
    """Мітка часу файлу у сховищі — інвалідує кеш після повторного імпорту."""
    path = config.STORE_DIR / f"{period_key}.parquet"
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data(show_spinner=False)
def _load_frame(period_key: str, token: float) -> pd.DataFrame:
    return store.load_period(period_key)


@st.cache_data(show_spinner=False)
def _validate(period_key: str, token: float) -> list[str]:
    return validate_frame(store.load_period(period_key))


def import_upload(uploaded) -> store.StoredPeriod:
    """Розібрати завантажений xlsx і покласти в сховище.

    Якщо файл з таким самим вмістом уже імпортовано, повторне читання не
    виконується — повертається наявний запис.
    """
    payload = uploaded.getvalue()
    digest = store.file_digest(payload)
    existing = store.find_by_hash(digest)
    if existing is not None:
        return existing
    frame = load_monthly_file(io.BytesIO(payload))
    return store.save_period(frame, uploaded.name, digest)


def result_for(period_key: str, settings: CalculationSettings) -> SettlementResult:
    """Розрахунок за збереженим періодом.

    Читання parquet кешується, сам розрахунок займає близько 45 мс, тому
    зміна параметрів у бічній панелі перераховується миттєво і без
    повторного завантаження файлу.
    """
    token = _cache_token(period_key)
    frame = _load_frame(period_key, token)
    entry = store.get_period(period_key)
    return calculate_settlement(
        frame,
        settings,
        source_name=entry.source_name if entry else "",
        warnings=_validate(period_key, token),
    )


def period_picker(label: str = "Розрахунковий період") -> str | None:
    """Вибір періоду зі сховища плюс завантаження нового файлу.

    Повертає ключ обраного періоду або ``None``, якщо сховище порожнє.
    """
    periods = store.list_periods()

    with st.expander("Завантажити файл гарантованого покупця", expanded=not periods):
        uploaded = st.file_uploader(
            "Місячний файл ГП (xlsx)",
            type=["xlsx", "xlsm"],
            help="Файл з 15 аркушами: прогноз, факт, ΔW, ціни, сальдовані обсяги, IEQ_GB.",
            key="upload_main",
        )
        if uploaded is not None:
            with st.spinner("Читання файлу…"):
                entry = import_upload(uploaded)
            st.success(
                f"{entry.month_label}: {entry.days} діб, {entry.hours} годин. "
                "Дані збережено — наступного разу файл не знадобиться."
            )
            st.session_state[KEY_PERIOD] = entry.period_key
            periods = store.list_periods()

    if not periods:
        st.info("Сховище порожнє. Завантажте місячний файл, щоб виконати розрахунок.")
        return None

    keys = [entry.period_key for entry in periods]
    labels = {entry.period_key: entry.month_label for entry in periods}
    current = st.session_state.get(KEY_PERIOD)
    index = keys.index(current) if current in keys else 0

    chosen = st.selectbox(
        label, keys, index=index, format_func=lambda key: labels[key], key="period_select"
    )
    st.session_state[KEY_PERIOD] = chosen
    return chosen


def store_manager() -> None:
    """Перелік збережених періодів з можливістю видалення."""
    periods = store.list_periods()
    if not periods:
        return
    with st.expander(f"Сховище даних ({len(periods)} періодів)", expanded=False):
        st.caption(
            f"Розібрані дані лежать у `{config.STORE_DIR}` у форматі parquet. "
            "Вихідні xlsx після імпорту не потрібні."
        )
        frame = pd.DataFrame(
            {
                "Період": [e.month_label for e in periods],
                "Діб": [e.days for e in periods],
                "Годин": [e.hours for e in periods],
                "Файл": [e.source_name for e in periods],
                "Імпортовано": [e.imported_at.replace("T", " ") for e in periods],
            }
        )
        st.dataframe(frame, width="stretch", hide_index=True)

        columns = st.columns([2, 1])
        target = columns[0].selectbox(
            "Видалити період",
            [e.period_key for e in periods],
            format_func=lambda key: dict((e.period_key, e.month_label) for e in periods)[key],
            key="delete_select",
        )
        if columns[1].button("Видалити", width="stretch"):
            store.delete_period(target)
            st.session_state.pop(KEY_PERIOD, None)
            reset_reports()
            st.rerun()


# ---------------------------------------------------------- параметри UI ----


def settings_sidebar(key_prefix: str = "main") -> CalculationSettings:
    """Панель параметрів розрахунку; значення за замовчуванням — з config."""
    with st.sidebar:
        st.header("Параметри розрахунку")
        st.caption(
            "Величини, яких немає у файлі ГП. Значення за замовчуванням звірені "
            "з виставленим рахунком за липень 2026."
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


# ------------------------------------------------------------- показники ----


def render_totals(result: SettlementResult) -> None:
    """Картки з місячними підсумками обсягів."""
    columns = st.columns(4)
    columns[0].metric("Прогноз, МВт·год", volume(result.total_forecast_mwh))
    columns[1].metric("Факт, МВт·год", volume(result.total_actual_mwh))
    columns[2].metric("Сальдо відхилення, МВт·год", volume(result.total_deviation_mwh))
    columns[3].metric("Годин з платежем", f"{result.billable_hours} з {result.hours_total}")


def render_curtailment(result: SettlementResult) -> None:
    """Картки з обмеженнями ОСП за місяць."""
    columns = st.columns(3)
    columns[0].metric("Всього обмеження, год.хв", duration(result.total_curtail_hours))
    columns[1].metric(
        "Всього обмежено виробіток, МВт·год", volume(result.total_curtailed_mwh)
    )
    columns[2].metric(
        "Діб з обмеженнями", f"{result.curtailed_days} з {len(result.daily)}"
    )
    st.caption(
        f"Тривалість — еквівалентна: у {result.curtailed_periods} год. з ΔW > 0 враховано "
        "частку години під обмеженням ΔW / (факт + ΔW), бо файл ГП подає обсяг "
        "невідпущеної енергії, а не час дії команди ОСП."
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
                alt.Tooltip("curtailed_mwh:Q", title="Обмежено, МВт·год", format=",.3f"),
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
        st.info("Спочатку оберіть період на сторінці «Головна».")
    return result
