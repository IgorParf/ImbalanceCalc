"""Консольний інтерфейс: розрахунок без UI.

Приклад:
    imbalance-calc "data/input/62W... липень 2026.xlsx" --pdf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import (
    DAILY_ALERT_THRESHOLD_UAH,
    DEFAULT_ALPHA,
    DEFAULT_K_E,
    DEFAULT_K_IM,
    DEFAULT_VAT_RATE,
    CalculationSettings,
)
from .core import calculate_from_file
from .exceptions import ImbalanceCalcError
from .reporting import build_excel_report, build_pdf_report, money


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="imbalance-calc", description=__doc__)
    parser.add_argument("input", type=Path, help="Місячний файл ГП (xlsx)")
    parser.add_argument("--pdf", action="store_true", help="Зберегти PDF-звіт")
    parser.add_argument("--excel", action="store_true", help="Зберегти xlsx-звіт")
    parser.add_argument(
        "-o", "--output-dir", type=Path,
        help="Тека для звітів (типово системна тека «Завантаження»)",
    )
    parser.add_argument("--k-e", type=float, default=DEFAULT_K_E, help="Допустиме відхилення, %%")
    parser.add_argument(
        "--alpha", type=float, default=DEFAULT_ALPHA, help="Частка відшкодування, %%"
    )
    parser.add_argument(
        "--k-im", type=float, default=DEFAULT_K_IM, help="Коефіцієнт ціни небалансу"
    )
    parser.add_argument("--vat", type=float, default=DEFAULT_VAT_RATE * 100, help="Ставка ПДВ, %%")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DAILY_ALERT_THRESHOLD_UAH,
        help="Поріг для аналізу по добах, грн (за замовчуванням 10000)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = CalculationSettings(
        k_e=args.k_e,
        alpha=args.alpha,
        k_im=args.k_im,
        vat_rate=args.vat / 100.0,
        daily_threshold_uah=args.threshold,
    )

    try:
        result = calculate_from_file(args.input, settings)
    except ImbalanceCalcError as error:
        print(f"Помилка: {error}", file=sys.stderr)
        return 1

    rate = settings.vat_rate * 100
    print(f"Період: {result.month_label} ({result.hours_total} год.)")
    print(f"Параметри: {settings.describe()}")
    for warning in result.warnings:
        print(f"  ! {warning}")
    print(f"Платіж без ПДВ:  {money(result.total_net)} грн")
    print(f"ПДВ {rate:g} %:        {money(result.vat)} грн")
    print(f"Всього з ПДВ:    {money(result.total_gross)} грн")

    alerts = result.alert_days
    threshold = money(settings.daily_threshold_uah, 0)
    print(f"\nДіб з платежем понад {threshold} грн: {len(alerts)} з {len(result.daily)}")
    for row in alerts.sort_values("cieq", ascending=False).itertuples(index=False):
        print(f"  {row.date:%d.%m.%Y}  {money(row.cieq):>16} грн  ({row.share_pct:.1f} % місяця)")

    if args.pdf:
        print(f"\nPDF-звіт: {build_pdf_report(result, args.output_dir)}")
    if args.excel:
        print(f"Excel-звіт: {build_excel_report(result, args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
