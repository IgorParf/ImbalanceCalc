"""Головна сторінка: вибір періоду, місячний підсумок і розрахунок по добах."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from imbalance_calc.dataio.schema import COLUMN_TITLES  # noqa: E402
from imbalance_calc.exceptions import ImbalanceCalcError  # noqa: E402
from imbalance_calc.reporting import (  # noqa: E402
    build_excel_bytes,
    build_pdf_report,
    daily_display,
    hourly_display,
    money,
    report_filename,
)
from imbalance_calc.ui.components import (  # noqa: E402
    KEY_PDF,
    KEY_RESULT,
    KEY_SIGNATURE,
    KEY_XLSX,
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
st.altair_chart(daily_chart(result), use_container_width=True)

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
        use_container_width=True,
        height=460,
    )

with tab_hourly:
    st.caption(
        "Повний погодинний розрахунок: власне відхилення, враховане відхилення W^α, "
        "ціни, сальдо групи, обраний сценарій (п. 2.1 Порядку) та платіж за годину."
    )
    st.dataframe(hourly_display(result.hours), use_container_width=True, height=460)

st.divider()

st.subheader("Звіт")
st.caption(
    "PDF зберігається у папку `reports/` у корені проєкту "
    f"(файл {report_filename(result)})."
)

columns = st.columns([1, 1, 2])

if columns[0].button("📄 Вивантажити звіт у PDF", type="primary", use_container_width=True):
    with st.spinner("Формування звіту…"):
        path = build_pdf_report(result)
    st.session_state[KEY_PDF] = (str(path), path.read_bytes())

if columns[1].button("📊 Сформувати Excel", use_container_width=True):
    with st.spinner("Формування файлу…"):
        st.session_state[KEY_XLSX] = build_excel_bytes(result)

pdf_saved = st.session_state.get(KEY_PDF)
if pdf_saved:
    saved_path, saved_bytes = pdf_saved
    st.success(f"Звіт збережено: `{saved_path}`")
    st.download_button(
        "⬇️ Завантажити копію PDF",
        data=saved_bytes,
        file_name=Path(saved_path).name,
        mime="application/pdf",
    )

xlsx_saved = st.session_state.get(KEY_XLSX)
if xlsx_saved:
    st.download_button(
        "⬇️ Завантажити Excel з погодинним розрахунком",
        data=xlsx_saved,
        file_name=f"imbalance-report_{result.period_key}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
