"""Створити синтетичний зразок місячного файлу ГП для демонстрації та тестів.

Запуск:  python scripts/make_sample.py [шлях]

Файл має ту саму структуру, що й реальний файл гарантованого покупця
(15 аркушів, доба × 24 години), але заповнений згенерованими даними —
реальні дані комерційного обліку в репозиторій не потрапляють.
"""

from __future__ import annotations

import math
import random
import sys
from calendar import monthrange
from datetime import date
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from imbalance_calc.console import prepare_console  # noqa: E402
from imbalance_calc.dataio.schema import HOURS_PER_DAY, SHEET_COLUMNS  # noqa: E402

YEAR, MONTH = 2026, 7
CAPACITY_MW = 10.0
SEED = 20260701


def solar_profile(hour: int, peak: float) -> float:
    """Спрощений добовий профіль СЕС: генерація з 6-ї по 21-у годину."""
    if hour < 6 or hour > 21:
        return -0.029  # нічне власне споживання
    phase = (hour - 6) / 15 * math.pi
    return round(peak * math.sin(phase) ** 1.4, 3)


def build() -> dict[str, list[list[float]]]:
    rng = random.Random(SEED)
    days = monthrange(YEAR, MONTH)[1]
    columns: dict[str, list[list[float]]] = {c: [] for c in SHEET_COLUMNS.values()}

    for _ in range(days):
        peak = CAPACITY_MW * rng.uniform(0.55, 1.0)
        w_pr, w_f, d_w = [], [], []
        for hour in range(1, HOURS_PER_DAY + 1):
            forecast = solar_profile(hour, peak)
            error = rng.gauss(0, max(abs(forecast), 0.05) * 0.18)
            actual = round(forecast + error, 4)
            curtailment = round(max(0.0, forecast) * 0.8, 3) if rng.random() < 0.01 else 0.0
            if curtailment:
                actual = round(max(-0.03, actual - curtailment), 4)
            w_pr.append(forecast)
            w_f.append(actual)
            d_w.append(curtailment)

        imsp, p_dam, sn, sp, ieq = [], [], [], [], []
        for _hour in range(HOURS_PER_DAY):
            day_ahead = round(rng.uniform(1500, 9000), 2)
            imbalance_price = round(day_ahead * rng.uniform(0.2, 2.4), 2)
            p_dam.append(day_ahead)
            imsp.append(imbalance_price)
            sn.append(round(-rng.uniform(20, 600), 6))
            sp.append(round(rng.uniform(10, 400), 6))
            ieq.append(round(rng.gauss(0, 200), 6))

        columns["w_pr"].append(w_pr)
        columns["w_f"].append(w_f)
        columns["d_w"].append(d_w)
        columns["imsp"].append(imsp)
        columns["p_dam"].append(p_dam)
        columns["sum_w_sn"].append(sn)
        columns["sum_w_sp"].append(sp)
        columns["ieq_gb"].append(ieq)

        # Похідні величини — так, щоб контрольні співвідношення сходилися
        w_s = [round(f - p, 6) for f, p in zip(w_f, w_pr, strict=True)]
        w_s_delta = [round(s + d, 6) for s, d in zip(w_s, d_w, strict=True)]
        d_sum_w = [round(d * rng.uniform(80, 140), 3) for d in d_w]
        sn_delta = [round(n + x * 0.4, 6) for n, x in zip(sn, d_sum_w, strict=True)]
        sp_delta = [round(p + x * 0.6, 6) for p, x in zip(sp, d_sum_w, strict=True)]
        columns["w_s"].append(w_s)
        columns["w_s_delta"].append(w_s_delta)
        columns["d_sum_w"].append([round(a + b - c - d, 6)
                                   for a, b, c, d in zip(sn_delta, sp_delta, sn, sp, strict=True)])
        columns["sum_w_sn_delta"].append(sn_delta)
        columns["sum_w_sp_delta"].append(sp_delta)
        columns["w_sum"].append([round(n + p, 6) for n, p in zip(sn, sp, strict=True)])
        columns["w_sum_delta"].append(
            [round(n + p, 6) for n, p in zip(sn_delta, sp_delta, strict=True)]
        )

    return columns


def save(path: Path) -> Path:
    columns = build()
    days = [date(YEAR, MONTH, d) for d in range(1, monthrange(YEAR, MONTH)[1] + 1)]

    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, column in SHEET_COLUMNS.items():
        ws = wb.create_sheet(sheet_name[:31])
        ws.append(["Доба", "Зона"] + [f"{h} год" for h in range(1, HOURS_PER_DAY + 1)])
        for index, day in enumerate(days):
            ws.append([day.strftime("%d.%m.%Y"), "IPS"] + list(columns[column][index]))

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


if __name__ == "__main__":
    prepare_console()
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parents[1] / "data" / "samples" / "sample_month_2026-07.xlsx"
    )
    print(f"Зразок збережено: {save(target)}")
