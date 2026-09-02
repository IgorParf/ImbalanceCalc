"""Головна сторінка: вибір періоду, місячний підсумок і розрахунок по добах."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from imbalance_calc.config import REPORTS_DIR  # noqa: E402
from imbalance_calc.dataio.schema import COLUMN_TITLES  # noqa: E402
from imbalance_calc.exceptions import ImbalanceCalcError  # noqa: E402
from imbalance_calc.reporting import (  # noqa: E402
    build_excel_bytes,
    build_pdf_bytes,
    daily_display,
    hourly_display,
    money,
    report_filename,
)
from imbalance_calc.ui.components import (  # noqa: E402
    KEY_PDF,
    KEY_PDF_PATH,
    KEY_RESULT,
    KEY_SIGNATURE,
    KEY_XLSX,
    KEY_XLSX_PATH,
    daily_chart,
    period_picker,
    render_curtailment,
    render_payment_block,
    render_totals,
    render_warnings,
    reset_reports,
    result_for,
    settings_sidebar,
    store_manager,
)
from imbalance_calc.ui.save_dialog import is_desktop, reveal, save_bytes  # noqa: E402

st.title("⚡ Розрахунок платежу за небаланси електричної енергії")
st.caption(
    "Порядок здійснення розрахунків балансуючої групи гарантованого покупця "
    "(Додаток 2 до Типового договору). Опис методики — docs/METHODOLOGY.md."
)

settings = settings_sidebar("main")

try:
    period_key = period_picker()
except ImbalanceCalcError as error:
    st.error(f"Не вдалося обробити файл: {error}")
    st.stop()

if period_key is None:
    st.session_state.pop(KEY_RESULT, None)
    reset_reports()
    st.stop()

result = result_for(period_key, settings)
st.session_state[KEY_RESULT] = result

signature = (period_key, settings)
if st.session_state.get(KEY_SIGNATURE) != signature:
    st.session_state[KEY_SIGNATURE] = signature
    reset_reports()

store_manager()
render_warnings(result)

st.subheader("Місячний підсумок")
render_totals(result)
render_curtailment(result)
render_payment_block(result)

st.divider()

st.subheader("Розрахунок по добах")
st.altair_chart(daily_chart(result), width="stretch")

alerts = result.alert_days
threshold = money(settings.daily_threshold_uah, 0)
if alerts.empty:
    st.info(f"Діб із платежем понад {threshold} грн немає.")
else:
    share = float(alerts["cieq"].sum()) / result.total_net * 100 if result.total_net else 0.0
    st.warning(
        f"Діб із платежем понад {threshold} грн — **{len(alerts)}** з {len(result.daily)}. "
        f"На них припадає **{money(float(alerts['cieq'].sum()))} грн** "
        f"({share:.1f} % місячного платежу без ПДВ). "
        "Детальний розбір — на сторінці «Аналіз»."
    )

tab_daily, tab_hourly = st.tabs(["По добах", "Погодинно"])

with tab_daily:
    st.dataframe(
        daily_display(result).style.format(
            {
                COLUMN_TITLES["w_pr"]: "{:,.3f}",
                COLUMN_TITLES["w_f"]: "{:,.3f}",
                COLUMN_TITLES["dev"]: "{:,.3f}",
                COLUMN_TITLES["w_alpha"]: "{:,.3f}",
                COLUMN_TITLES["curtailed_mwh"]: "{:,.3f}",
                COLUMN_TITLES["max_hour_cieq"]: "{:,.2f}",
                COLUMN_TITLES["cieq"]: "{:,.2f}",
                COLUMN_TITLES["share_pct"]: "{:.1f}",
            }
        ).map(
            lambda v: "background-color: #fde9e7" if v is True else "",
            subset=[COLUMN_TITLES["exceeds_threshold"]],
        ),
        width="stretch",
        height=460,
    )

with tab_hourly:
    st.caption(
        "Повний погодинний розрахунок: власне відхилення, враховане відхилення W^α, "
        "ціни, сальдо групи, обраний сценарій (п. 2.1 Порядку) та платіж за годину."
    )
    st.dataframe(hourly_display(result.hours), width="stretch", height=460)

st.divider()

st.subheader("Звіт")

pdf_name = report_filename(result)
xlsx_name = f"imbalance-report_{result.period_key}.xlsx"

if is_desktop():
    st.caption(
        f"Після формування відкриється діалог вибору теки; "
        f"за замовчуванням — «{REPORTS_DIR}»."
    )
else:
    st.caption(
        f"Файл завантажиться у теку завантажень браузера (зазвичай «{REPORTS_DIR}»). "
        "Щоб щоразу обирати теку, увімкніть у браузері «Завжди питати, куди зберігати файли»."
    )

columns = st.columns([1, 1, 2])
make_pdf = columns[0].button(
    "📄 Вивантажити звіт у PDF", type="primary", width="stretch"
)
make_xlsx = columns[1].button("📊 Сформувати Excel", width="stretch")

if make_pdf:
    with st.spinner("Формування звіту…"):
        payload = build_pdf_bytes(result)
    st.session_state[KEY_PDF] = payload
    if is_desktop():
        saved = save_bytes(payload, pdf_name, REPORTS_DIR)
        st.session_state[KEY_PDF_PATH] = str(saved) if saved else ""

if make_xlsx:
    with st.spinner("Формування файлу…"):
        payload = build_excel_bytes(result)
    st.session_state[KEY_XLSX] = payload
    if is_desktop():
        saved = save_bytes(payload, xlsx_name, REPORTS_DIR)
        st.session_state[KEY_XLSX_PATH] = str(saved) if saved else ""


def _offer(payload: bytes | None, path_key: str, name: str, mime: str, label: str) -> None:
    """Показати результат збереження або кнопку завантаження для браузера."""
    if not payload:
        return
    if is_desktop():
        saved_path = st.session_state.get(path_key)
        if saved_path:
            st.success(f"Збережено: `{saved_path}`")
            if st.button(f"📂 Показати в Провіднику: {Path(saved_path).name}"):
                reveal(saved_path)
        else:
            st.info("Збереження скасовано.")
        return
    st.download_button(label, data=payload, file_name=name, mime=mime)


_offer(
    st.session_state.get(KEY_PDF),
    KEY_PDF_PATH,
    pdf_name,
    "application/pdf",
    "⬇️ Завантажити PDF",
)
_offer(
    st.session_state.get(KEY_XLSX),
    KEY_XLSX_PATH,
    xlsx_name,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "⬇️ Завантажити Excel з погодинним розрахунком",
)
