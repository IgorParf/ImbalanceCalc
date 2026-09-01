"""Сторінка аналізу: загальний, по добах та порівняння з іншим місяцем."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from imbalance_calc import store  # noqa: E402
from imbalance_calc.core import worst_hours  # noqa: E402
from imbalance_calc.dataio.schema import COLUMN_TITLES  # noqa: E402
from imbalance_calc.exceptions import ImbalanceCalcError  # noqa: E402
from imbalance_calc.reporting import (  # noqa: E402
    compare,
    daily_comparison,
    daily_display,
    duration,
    money,
    summary_text,
    volume,
)
from imbalance_calc.ui.components import (  # noqa: E402
    KEY_COMPARE,
    daily_chart,
    import_upload,
    require_result,
    result_for,
)

st.title("📊 Аналіз небалансів")

result = require_result()
if result is None:
    st.stop()

settings = result.settings
threshold = money(settings.daily_threshold_uah, 0)
st.caption(summary_text(result))

tab_general, tab_daily, tab_compare = st.tabs(
    ["Загальний аналіз", "Аналіз по добах", "Порівняння з іншим місяцем"]
)

# ---------------------------------------------------------------- загальний --
with tab_general:
    hours = result.hours
    columns = st.columns(4)
    columns[0].metric("Платіж без ПДВ, грн", money(result.total_net))
    columns[1].metric("Всього з ПДВ, грн", money(result.total_gross))
    columns[2].metric("Середня вартість, грн/МВт·год", money(result.avg_cost_per_mwh))
    columns[3].metric(
        "Частка тарифікованих годин",
        f"{result.billable_hours / result.hours_total * 100:.1f} %",
    )

    columns = st.columns(3)
    columns[0].metric("Всього обмеження, год.хв", duration(result.total_curtail_hours))
    columns[1].metric("Всього обмежено виробіток, МВт·год", volume(result.total_curtailed_mwh))
    lost_share = (
        result.total_curtailed_mwh / (result.total_actual_mwh + result.total_curtailed_mwh) * 100
        if result.total_actual_mwh + result.total_curtailed_mwh
        else 0.0
    )
    columns[2].metric("Втрачено від потенціалу", f"{lost_share:.1f} %")

    st.markdown("##### Концентрація платежу")
    ordered = result.daily.sort_values("cieq", ascending=False).reset_index(drop=True)
    if result.total_net <= 0:
        st.info("За цей місяць платіж за небаланси не нараховано.")
        st.stop()
    ordered["cumulative_pct"] = ordered["cieq"].cumsum() / result.total_net * 100
    days_80 = int((ordered["cumulative_pct"] < 80).sum()) + 1
    top_day = ordered.iloc[0]
    st.write(
        f"80 % місячного платежу формують **{days_80}** діб з {len(result.daily)}. "
        f"Найдорожча доба — **{top_day['date']:%d.%m.%Y}** "
        f"({money(top_day['cieq'])} грн, {top_day['share_pct']:.1f} % місяця)."
    )

    pareto = (
        alt.Chart(ordered.assign(n=ordered.index + 1))
        .mark_line(point=True, color="#1f4e79")
        .encode(
            x=alt.X("n:Q", title="кількість діб (від найдорожчої)"),
            y=alt.Y("cumulative_pct:Q", title="накопичена частка платежу, %"),
            tooltip=[
                alt.Tooltip("date:T", title="Доба", format="%d.%m.%Y"),
                alt.Tooltip("cieq:Q", title="Платіж, грн", format=",.2f"),
                alt.Tooltip("cumulative_pct:Q", title="Накопичено, %", format=".1f"),
            ],
        )
        .properties(height=240)
    )
    st.altair_chart(pareto, use_container_width=True)

    st.markdown("##### Платіж за годинами доби")
    by_hour = hours.groupby("hour", as_index=False).agg(
        cieq=("cieq", "sum"), billed=("cieq", lambda s: int((s > 0).sum()))
    )
    hour_chart = (
        alt.Chart(by_hour)
        .mark_bar(color="#5b8db8")
        .encode(
            x=alt.X("hour:O", title="година доби"),
            y=alt.Y("cieq:Q", title="платіж за місяць, грн"),
            tooltip=[
                alt.Tooltip("hour:O", title="Година"),
                alt.Tooltip("cieq:Q", title="Платіж, грн", format=",.2f"),
                alt.Tooltip("billed:Q", title="Годин з платежем"),
            ],
        )
        .properties(height=240)
    )
    st.altair_chart(hour_chart, use_container_width=True)

    st.markdown("##### Карта платежів «доба × година»")
    heat_source = hours.assign(day=pd.to_datetime(hours["date"]).dt.day)
    heatmap = (
        alt.Chart(heat_source)
        .mark_rect()
        .encode(
            x=alt.X("day:O", title="доба"),
            y=alt.Y("hour:O", title="година"),
            color=alt.Color(
                "cieq:Q", title="грн", scale=alt.Scale(scheme="orangered", domainMin=0)
            ),
            tooltip=[
                alt.Tooltip("day:O", title="Доба"),
                alt.Tooltip("hour:O", title="Година"),
                alt.Tooltip("cieq:Q", title="Платіж, грн", format=",.2f"),
                alt.Tooltip("dev:Q", title="Відхилення, МВт·год", format=",.3f"),
                alt.Tooltip("imsp:Q", title="Ціна небалансу", format=",.2f"),
            ],
        )
        .properties(height=380)
    )
    st.altair_chart(heatmap, use_container_width=True)

    st.markdown("##### Найдорожчі години")
    st.dataframe(
        worst_hours(hours, 15).rename(columns=COLUMN_TITLES),
        use_container_width=True,
        hide_index=True,
    )

    scenarios = hours["scenario"].value_counts()
    st.caption(
        "Обраний сценарій за п. 2.1 Порядку: "
        + ", ".join(f"{name} — {count} год." for name, count in scenarios.items())
        + ". Години поза «мертвою зоною» K_e: "
        + f"{int(hours['billable'].sum())} з {result.hours_total}."
    )

# ----------------------------------------------------------------- по добах --
with tab_daily:
    st.altair_chart(daily_chart(result), use_container_width=True)

    alerts = result.alert_days.sort_values("cieq", ascending=False)
    st.markdown(f"##### Доби з платежем понад {threshold} грн")
    if alerts.empty:
        st.info(f"Таких діб немає — усі добові платежі не перевищують {threshold} грн.")
    else:
        rate = settings.vat_rate
        columns = st.columns(3)
        columns[0].metric("Діб понад поріг", f"{len(alerts)} з {len(result.daily)}")
        columns[1].metric("Сума без ПДВ, грн", money(float(alerts["cieq"].sum())))
        columns[2].metric(
            "Частка у місяці",
            f"{float(alerts['cieq'].sum()) / result.total_net * 100:.1f} %"
            if result.total_net
            else "0,0 %",
        )
        display = alerts.assign(
            vat=alerts["cieq"] * rate, gross=alerts["cieq"] * (1 + rate)
        )[
            [
                "date", "cieq", "vat", "gross", "hours_billed",
                "curtail_hours", "curtailed_mwh", "dev", "share_pct",
            ]
        ].copy()
        display["date"] = pd.to_datetime(display["date"]).dt.strftime("%d.%m.%Y")
        display["curtail_hours"] = display["curtail_hours"].map(duration)
        display.columns = [
            "Доба", "Платіж без ПДВ, грн", "ПДВ, грн", "З ПДВ, грн", "Годин з платежем",
            "Обмеження, год.хв", "Обмежено виробіток, МВт·год",
            "Відхилення, МВт·год", "Частка у місяці, %",
        ]
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("##### Деталізація доби")
    days = list(result.daily["date"])
    default_index = days.index(alerts.iloc[0]["date"]) if not alerts.empty else 0
    chosen = st.selectbox(
        "Оберіть добу", days, index=default_index, format_func=lambda d: f"{d:%d.%m.%Y}"
    )
    day_hours = result.hours[result.hours["date"] == chosen]
    day_row = result.daily[result.daily["date"] == chosen].iloc[0]

    columns = st.columns(5)
    columns[0].metric("Платіж без ПДВ, грн", money(day_row["cieq"]))
    columns[1].metric("З ПДВ, грн", money(day_row["cieq"] * (1 + settings.vat_rate)))
    columns[2].metric("Відхилення, МВт·год", volume(day_row["dev"]))
    columns[3].metric("Обмеження, год.хв", duration(day_row["curtail_hours"]))
    columns[4].metric("Обмежено, МВт·год", volume(day_row["curtailed_mwh"]))

    detail = day_hours.assign(Прогноз=day_hours["w_pr"], Факт=day_hours["w_f"]).melt(
        id_vars="hour", value_vars=["Прогноз", "Факт"], var_name="Ряд", value_name="МВт·год"
    )
    profile = (
        alt.Chart(detail)
        .mark_line(point=True)
        .encode(
            x=alt.X("hour:O", title="година"),
            y=alt.Y("МВт·год:Q"),
            color=alt.Color(
                "Ряд:N",
                scale=alt.Scale(domain=["Прогноз", "Факт"], range=["#9aa7b4", "#1f4e79"]),
                legend=alt.Legend(title=None, orient="top"),
            ),
        )
        .properties(height=220)
    )
    payment = (
        alt.Chart(day_hours)
        .mark_bar(color="#c0392b")
        .encode(
            x=alt.X("hour:O", title="година"),
            y=alt.Y("cieq:Q", title="платіж, грн"),
            tooltip=[
                alt.Tooltip("hour:O", title="Година"),
                alt.Tooltip("cieq:Q", title="Платіж, грн", format=",.2f"),
                alt.Tooltip("dev:Q", title="Відхилення, МВт·год", format=",.3f"),
                alt.Tooltip("dev_pct:Q", title="Відхилення, %", format=",.1f"),
                alt.Tooltip("d_w:Q", title="Обмежено, МВт·год", format=",.3f"),
                alt.Tooltip("imsp:Q", title="Ціна небалансу", format=",.2f"),
                alt.Tooltip("p_dam:Q", title="Ціна РДН", format=",.2f"),
            ],
        )
        .properties(height=220)
    )
    st.altair_chart(profile, use_container_width=True)
    st.altair_chart(payment, use_container_width=True)

    st.markdown("##### Добові підсумки")
    st.dataframe(daily_display(result), use_container_width=True, hide_index=True)

# -------------------------------------------------------------- порівняння --
with tab_compare:
    candidates = [e for e in store.list_periods() if e.period_key != result.period_key]
    default_entry = store.comparison_candidate(result.period_key)

    if candidates:
        keys = [entry.period_key for entry in candidates]
        labels = {entry.period_key: entry.month_label for entry in candidates}
        index = keys.index(default_entry.period_key) if default_entry else 0
        chosen_key = st.selectbox(
            "Період для порівняння",
            keys,
            index=index,
            format_func=lambda key: labels[key],
            help="За замовчуванням обирається попередній місяць.",
        )
        if default_entry and chosen_key == default_entry.period_key:
            st.caption(f"Попередній місяць у сховищі: {labels[chosen_key]}.")
    else:
        chosen_key = None
        st.info(
            "У сховищі лише один період. Завантажте файл іншого місяця — "
            "порівняння за замовчуванням робиться з попереднім місяцем."
        )

    with st.expander("Завантажити ще один місяць", expanded=not candidates):
        other_file = st.file_uploader(
            "Файл для порівняння (xlsx)", type=["xlsx", "xlsm"], key="compare_upload"
        )
        if other_file is not None:
            try:
                with st.spinner("Читання файлу…"):
                    entry = import_upload(other_file)
            except ImbalanceCalcError as error:
                st.error(f"Не вдалося обробити файл: {error}")
                st.stop()
            st.success(f"Додано до сховища: {entry.month_label}.")
            chosen_key = entry.period_key

    if chosen_key is None:
        st.stop()

    other = result_for(chosen_key, settings)
    st.session_state[KEY_COMPARE] = other

    delta = other.total_net - result.total_net
    columns = st.columns(3)
    columns[0].metric(f"{result.month_label}, грн без ПДВ", money(result.total_net))
    columns[1].metric(
        f"{other.month_label}, грн без ПДВ",
        money(other.total_net),
        delta=money(delta),
        delta_color="inverse",
    )
    columns[2].metric(
        "Зміна", f"{delta / result.total_net * 100:+.1f} %" if result.total_net else "—"
    )

    st.markdown("##### Показники")
    comparison = compare(result, other)
    st.dataframe(
        comparison.style.format(
            {col: "{:,.2f}" for col in comparison.columns if col != "Показник"}
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("##### Платіж по добах")
    daily_pair = daily_comparison(result, other)
    long = daily_pair.melt(id_vars="День", var_name="Місяць", value_name="Платіж, грн")
    chart = (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("День:O"),
            y=alt.Y("Платіж, грн:Q"),
            color=alt.Color("Місяць:N", legend=alt.Legend(title=None, orient="top")),
            xOffset="Місяць:N",
            tooltip=["День:O", "Місяць:N", alt.Tooltip("Платіж, грн:Q", format=",.2f")],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)

    st.markdown(f"##### Доби понад {threshold} грн")
    left, right = st.columns(2)
    for column, item in ((left, result), (right, other)):
        with column:
            st.caption(item.month_label)
            item_alerts = item.alert_days.sort_values("cieq", ascending=False)
            if item_alerts.empty:
                st.info("Немає")
            else:
                frame = item_alerts[["date", "cieq", "share_pct"]].copy()
                frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%d.%m.%Y")
                frame.columns = ["Доба", "Платіж без ПДВ, грн", "Частка у місяці, %"]
                st.dataframe(frame, use_container_width=True, hide_index=True)
