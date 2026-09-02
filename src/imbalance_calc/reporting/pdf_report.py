"""Формування PDF-звіту про розрахунок небалансів.

Кирилиця в reportlab потребує TTF-шрифту: використовується DejaVu Sans, який
постачається разом із matplotlib, з відкатом на системні шрифти Windows.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4, landscape  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .. import config  # noqa: E402
from ..models import SettlementResult  # noqa: E402
from .summary import duration, money, totals_rows, volume  # noqa: E402

FONT_REGULAR = "Report"
FONT_BOLD = "Report-Bold"

_ACCENT = colors.HexColor("#1f4e79")
_ALERT_BG = colors.HexColor("#fde9e7")
_HEAD_BG = colors.HexColor("#eef2f7")
_GRID = colors.HexColor("#c8d0da")


def _font_candidates() -> list[tuple[str, str]]:
    """Пари (звичайний, жирний) шрифтів з підтримкою кирилиці."""
    mpl_fonts = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    windows = Path("C:/Windows/Fonts")
    return [
        (str(mpl_fonts / "DejaVuSans.ttf"), str(mpl_fonts / "DejaVuSans-Bold.ttf")),
        (str(windows / "arial.ttf"), str(windows / "arialbd.ttf")),
        (str(windows / "segoeui.ttf"), str(windows / "segoeuib.ttf")),
    ]


def _register_fonts() -> None:
    """Зареєструвати кириличний шрифт (один раз на процес)."""
    if FONT_REGULAR in pdfmetrics.getRegisteredFontNames():
        return
    for regular, bold in _font_candidates():
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, regular))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, bold))
            pdfmetrics.registerFontFamily(FONT_REGULAR, normal=FONT_REGULAR, bold=FONT_BOLD)
            return
    raise RuntimeError(
        "Не знайдено TTF-шрифту з кирилицею для PDF. "
        "Встановіть matplotlib або перевірте наявність Arial у C:/Windows/Fonts."
    )


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName=FONT_BOLD, fontSize=16, spaceAfter=4,
            textColor=_ACCENT,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=9,
            textColor=colors.HexColor("#5a6674"), spaceAfter=10, alignment=1,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=12,
            textColor=_ACCENT, spaceBefore=12, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=9, leading=12,
        ),
        "note": ParagraphStyle(
            "note", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=8,
            textColor=colors.HexColor("#5a6674"), leading=11,
        ),
    }


def _table_style(header: bool = True) -> TableStyle:
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        commands += [
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ]
    return TableStyle(commands)


def _daily_chart(result: SettlementResult) -> io.BytesIO:
    """Стовпчикова діаграма платежів по добах із лінією порогу."""
    daily = result.daily
    days = [d.day for d in daily["date"]]
    values = daily["cieq"].to_numpy()
    threshold = result.settings.daily_threshold_uah
    palette = ["#c0392b" if v > threshold else "#5b8db8" for v in values]

    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=200)
    ax.bar(days, values, color=palette, width=0.7)
    ax.axhline(threshold, color="#c0392b", linewidth=0.9, linestyle="--")
    ax.annotate(
        f"поріг {threshold:,.0f} грн".replace(",", " "),
        xy=(days[0], threshold), xytext=(0, 4), textcoords="offset points",
        fontsize=7, color="#c0392b",
    )
    ax.set_xlabel("доба", fontsize=8)
    ax.set_ylabel("платіж без ПДВ, грн", fontsize=8)
    ax.set_xticks(days)
    ax.tick_params(labelsize=6.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", linewidth=0.4, alpha=0.35)
    ax.margins(x=0.01)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _totals_table(result: SettlementResult) -> Table:
    rows = [[label, value] for label, value in totals_rows(result)]
    table = Table(rows, colWidths=[110 * mm, 55 * mm], hAlign="LEFT")
    style = _table_style(header=False)
    style.add("ALIGN", (0, 0), (0, -1), "LEFT")
    # Три підсумкові рядки — платіж, ПДВ, всього з ПДВ
    style.add("FONTNAME", (0, -3), (-1, -1), FONT_BOLD)
    style.add("BACKGROUND", (0, -1), (-1, -1), _HEAD_BG)
    style.add("TEXTCOLOR", (0, -1), (-1, -1), _ACCENT)
    table.setStyle(style)
    return table


def _daily_table(result: SettlementResult) -> Table:
    header = [
        "Доба", "Прогноз,\nМВт·год", "Факт,\nМВт·год", "Відхилення,\nМВт·год",
        "Обмеження,\nгод.хв", "Обмежено\nвиробіток,\nМВт·год",
        "Годин з\nплатежем", "Платіж без\nПДВ, грн", "Частка,\n%",
    ]
    rows = [header]
    alert_rows: list[int] = []
    for index, row in enumerate(result.daily.itertuples(index=False), start=1):
        if row.exceeds_threshold:
            alert_rows.append(index)
        rows.append([
            row.date.strftime("%d.%m.%Y"),
            volume(row.w_pr), volume(row.w_f), volume(row.dev),
            duration(row.curtail_hours), volume(row.curtailed_mwh),
            str(int(row.hours_billed)),
            money(row.cieq), f"{row.share_pct:.1f}",
        ])
    rows.append([
        "Разом",
        volume(result.total_forecast_mwh), volume(result.total_actual_mwh),
        volume(result.total_deviation_mwh),
        duration(result.total_curtail_hours), volume(result.total_curtailed_mwh),
        str(result.billable_hours),
        money(result.total_net), "100,0",
    ])

    widths = [24, 28, 28, 30, 26, 30, 24, 32, 18]
    table = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1, hAlign="LEFT")
    style = _table_style()
    style.add("ALIGN", (0, 1), (0, -1), "LEFT")
    style.add("FONTNAME", (0, -1), (-1, -1), FONT_BOLD)
    style.add("BACKGROUND", (0, -1), (-1, -1), _HEAD_BG)
    for row_index in alert_rows:
        style.add("BACKGROUND", (0, row_index), (-1, row_index), _ALERT_BG)
    table.setStyle(style)
    return table


def _alert_table(result: SettlementResult) -> Table:
    alerts = result.alert_days.sort_values("cieq", ascending=False)
    header = [
        "Доба", "Платіж без ПДВ, грн", "ПДВ, грн", "З ПДВ, грн",
        "Годин з платежем", "Макс. за годину, грн", "Відхилення, МВт·год", "Частка у місяці, %",
    ]
    rows = [header]
    rate = result.settings.vat_rate
    for row in alerts.itertuples(index=False):
        rows.append([
            row.date.strftime("%d.%m.%Y"),
            money(row.cieq), money(row.cieq * rate), money(row.cieq * (1 + rate)),
            str(int(row.hours_billed)), money(row.max_hour_cieq),
            volume(row.dev), f"{row.share_pct:.1f}",
        ])
    total = float(alerts["cieq"].sum())
    rows.append([
        "Разом", money(total), money(total * rate), money(total * (1 + rate)),
        str(int(alerts["hours_billed"].sum())), "", volume(float(alerts["dev"].sum())),
        f"{alerts['share_pct'].sum():.1f}",
    ])

    widths = [26, 34, 30, 34, 26, 36, 34, 26]
    table = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1, hAlign="LEFT")
    style = _table_style()
    style.add("ALIGN", (0, 1), (0, -1), "LEFT")
    style.add("FONTNAME", (0, -1), (-1, -1), FONT_BOLD)
    style.add("BACKGROUND", (0, -1), (-1, -1), _HEAD_BG)
    table.setStyle(style)
    return table


def build_report_story(result: SettlementResult) -> list:
    """Зібрати вміст звіту (список flowable-елементів reportlab)."""
    styles = _styles()
    threshold = money(result.settings.daily_threshold_uah, 0)
    story: list = [
        Paragraph("Розрахунок платежу за небаланси електричної енергії", styles["title"]),
        Paragraph(
            f"Розрахунковий період: {result.month_label}"
            + (f" &nbsp;|&nbsp; файл: {result.source_name}" if result.source_name else "")
            + f" &nbsp;|&nbsp; сформовано: {datetime.now():%d.%m.%Y %H:%M}",
            styles["subtitle"],
        ),
        Paragraph("Підсумок за місяць", styles["h2"]),
        _totals_table(result),
        Spacer(1, 4 * mm),
        Paragraph(f"Параметри розрахунку: {result.settings.describe()}.", styles["note"]),
        Paragraph(
            "Розрахунок виконано за Порядком здійснення розрахунків балансуючої групи "
            "гарантованого покупця (Додаток 2 до Типового договору про участь у балансуючій "
            "групі гарантованого покупця).",
            styles["note"],
        ),
        Paragraph("Платіж по добах", styles["h2"]),
        Image(_daily_chart(result), width=250 * mm, height=80 * mm),
        Spacer(1, 3 * mm),
        _daily_table(result),
        PageBreak(),
        Paragraph(f"Доби з платежем понад {threshold} грн", styles["h2"]),
    ]

    if result.alert_days.empty:
        story.append(
            Paragraph(
                f"Діб із платежем понад {threshold} грн у цьому місяці немає.", styles["body"]
            )
        )
    else:
        alerts = result.alert_days
        share = float(alerts["cieq"].sum()) / result.total_net * 100 if result.total_net else 0.0
        story += [
            Paragraph(
                f"Таких діб — {len(alerts)} з {len(result.daily)}; "
                f"на них припадає {share:.1f} % місячного платежу "
                f"({money(float(alerts['cieq'].sum()))} грн без ПДВ).",
                styles["body"],
            ),
            Spacer(1, 3 * mm),
            _alert_table(result),
        ]

    if result.warnings:
        story += [
            Paragraph("Зауваження до вхідних даних", styles["h2"]),
            *[Paragraph(f"• {w}", styles["body"]) for w in result.warnings],
        ]
    return story


def build_pdf_bytes(result: SettlementResult) -> bytes:
    """Сформувати PDF-звіт у пам'яті."""
    _register_fonts()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title=f"Небаланси {result.month_label}",
        author="ImbalanceCalc",
    )
    doc.build(build_report_story(result))
    return buffer.getvalue()


def report_filename(result: SettlementResult) -> str:
    """Ім'я файлу звіту: ``imbalance-report_2026-07_20260901-1215.pdf``."""
    return f"imbalance-report_{result.period_key}_{datetime.now():%Y%m%d-%H%M}.pdf"


def build_pdf_report(result: SettlementResult, directory: Path | str | None = None) -> Path:
    """Зберегти PDF-звіт у теку ``directory`` (типово «Завантаження»)."""
    target_dir = Path(directory) if directory else config.REPORTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / report_filename(result)
    path.write_bytes(build_pdf_bytes(result))
    return path
