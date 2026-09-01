"""Завантаження даних з файлів (xlsx/xls/csv) у нормалізований вигляд."""

from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd

from ..models import PeriodRecord


def load_dataframe(source: str | Path | IO[bytes], *, sheet: str | int = 0) -> pd.DataFrame:
    """Прочитати файл і повернути DataFrame з канонічними назвами колонок.

    TODO: визначення формату за розширенням/сигнатурою, пошук рядка заголовків,
    приведення назв колонок через ``COLUMN_ALIASES``.
    """
    raise NotImplementedError


def load_records(source: str | Path | IO[bytes]) -> list[PeriodRecord]:
    """Прочитати файл і повернути список розрахункових періодів.

    TODO: конвертація DataFrame -> ``PeriodRecord`` з приведенням до Decimal.
    """
    raise NotImplementedError
