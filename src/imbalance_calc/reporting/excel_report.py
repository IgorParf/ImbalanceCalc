"""Вивантаження результату розрахунку в Excel."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from .. import config
from ..models import SettlementResult
from .summary import daily_display, hourly_display, totals_rows


def _write(result: SettlementResult, writer: pd.ExcelWriter) -> None:
    pd.DataFrame(totals_rows(result), columns=["Показник", "Значення"]).to_excel(
        writer, sheet_name="Підсумок", index=False
    )
    daily_display(result).to_excel(writer, sheet_name="По добах", index=False)
    alerts = result.alert_days
    if not alerts.empty:
        display = daily_display(result)
        display[result.daily["exceeds_threshold"].to_numpy()].to_excel(
            writer, sheet_name="Понад поріг", index=False
        )
    hourly_display(result.hours).to_excel(writer, sheet_name="Погодинно", index=False)


def build_excel_bytes(result: SettlementResult) -> bytes:
    """Сформувати xlsx-звіт у пам'яті."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        _write(result, writer)
    return buffer.getvalue()


def build_excel_report(result: SettlementResult, directory: Path | str | None = None) -> Path:
    """Зберегти xlsx-звіт у теку ``directory`` (типово «Завантаження»)."""
    target_dir = Path(directory) if directory else config.REPORTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"imbalance-report_{result.period_key}.xlsx"
    path.write_bytes(build_excel_bytes(result))
    return path
