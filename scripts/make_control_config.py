"""Створити заготовку data/input/control.json для звірки з рахунком.

Запуск:  python scripts/make_control_config.py [файл.xlsx]

Файл не відстежується git: реальні дані комерційного обліку та суми рахунків
у репозиторій не потрапляють. Після створення впишіть у нього суму з рахунку
без ПДВ, і тест tests/test_control_example.py почне її контролювати.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from imbalance_calc.config import (  # noqa: E402
    DEFAULT_ALPHA,
    DEFAULT_K_E,
    DEFAULT_K_IM,
    INPUT_DIR,
)
from imbalance_calc.console import prepare_console  # noqa: E402

TARGET = INPUT_DIR / "control.json"


def find_monthly_file() -> Path | None:
    """Єдиний xlsx у data/input — найімовірніше і є місячним файлом ГП."""
    candidates = [p for p in INPUT_DIR.glob("*.xlsx") if not p.name.startswith("~$")]
    return candidates[0] if len(candidates) == 1 else None


def build(source: Path) -> dict:
    from imbalance_calc.core import calculate_from_file

    result = calculate_from_file(source)
    return {
        "file": source.name,
        "_підказка": "Впишіть у total_net_uah суму без ПДВ з рахунку ГП.",
        "total_net_uah": round(result.total_net, 2),
        "k_e": DEFAULT_K_E,
        "alpha": DEFAULT_ALPHA,
        "k_im": DEFAULT_K_IM,
        "period_key": result.period_key,
        "hours": result.hours_total,
    }


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if argv:
        source = Path(argv[0])
    else:
        found = find_monthly_file()
        if found is None:
            print(
                f"Покладіть місячний файл ГП у {INPUT_DIR} або вкажіть шлях "
                "аргументом.",
                file=sys.stderr,
            )
            return 1
        source = found

    if not source.exists():
        print(f"Не знайдено файл {source}", file=sys.stderr)
        return 1

    if TARGET.exists():
        print(f"{TARGET} вже існує — залишаю без змін.")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(build(source), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Створено {TARGET}. Звірте total_net_uah із сумою у рахунку.")
    return 0


if __name__ == "__main__":
    prepare_console()
    raise SystemExit(main())
