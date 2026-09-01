"""Консольний інтерфейс: розрахунок без UI.

Приклад:
    imbalance-calc data/input/2025-08.xlsx -o data/output/report.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DAILY_ALERT_THRESHOLD_UAH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="imbalance-calc", description=__doc__)
    parser.add_argument("input", type=Path, help="Вхідний файл з даними (xlsx/csv)")
    parser.add_argument("-o", "--output", type=Path, help="Шлях до Excel-звіту")
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(DAILY_ALERT_THRESHOLD_UAH),
        help="Поріг для аналізу по добах, грн (за замовчуванням 10000)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # TODO: load_records -> calculate_settlement -> build_excel_report
    raise NotImplementedError(f"Розрахунок для {args.input} ще не реалізовано")


if __name__ == "__main__":
    raise SystemExit(main())
