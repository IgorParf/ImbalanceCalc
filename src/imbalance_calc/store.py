"""Локальне сховище розібраних місячних файлів у форматі parquet.

Навіщо: читання xlsx займає ~250 мс, читання того самого набору з parquet —
~7 мс, тобто у ~34 рази швидше. Сам розрахунок дешевий (~45 мс), тому в
сховищі лежать **розібрані вхідні дані**, а не готові результати: параметри
(K_e, alpha, K_im, ПДВ, поріг) можна змінювати без ризику показати застарілі
числа, а відкриття сторінки все одно не потребує повторного завантаження файлу.

Структура:
    data/store/index.json           перелік періодів з метаданими
    data/store/2026-07.parquet      погодинна таблиця за період
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import config
from .models import UKR_MONTHS

INDEX_NAME = "index.json"
COMPRESSION = "zstd"


@dataclass(frozen=True)
class StoredPeriod:
    """Метадані одного збереженого періоду."""

    period_key: str          # 2026-07
    month_label: str         # липень 2026
    source_name: str         # ім'я вихідного xlsx
    file_hash: str           # sha256 вмісту вихідного файлу
    days: int
    hours: int
    imported_at: str         # ISO-8601

    @property
    def year(self) -> int:
        return int(self.period_key[:4])

    @property
    def month(self) -> int:
        return int(self.period_key[5:7])


def file_digest(payload: bytes) -> str:
    """Хеш вмісту файлу — щоб розпізнати повторне завантаження того самого."""
    return hashlib.sha256(payload).hexdigest()


def _store_dir(directory: Path | str | None = None) -> Path:
    path = Path(directory) if directory else config.STORE_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _index_path(directory: Path | str | None = None) -> Path:
    return _store_dir(directory) / INDEX_NAME


def _read_index(directory: Path | str | None = None) -> dict[str, StoredPeriod]:
    path = _index_path(directory)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {key: StoredPeriod(**value) for key, value in raw.items()}


def _write_index(index: dict[str, StoredPeriod], directory: Path | str | None = None) -> None:
    payload = {key: asdict(value) for key, value in index.items()}
    _index_path(directory).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def period_key_of(frame: pd.DataFrame) -> str:
    """Ключ періоду ``РРРР-ММ`` за першою добою таблиці."""
    first = min(frame["date"])
    return f"{first.year:04d}-{first.month:02d}"


def month_label_of(period_key: str) -> str:
    """«липень 2026» за ключем ``2026-07``."""
    year, month = int(period_key[:4]), int(period_key[5:7])
    return f"{UKR_MONTHS.get(month, month)} {year}"


def previous_period_key(period_key: str) -> str:
    """Ключ попереднього календарного місяця."""
    year, month = int(period_key[:4]), int(period_key[5:7])
    return f"{year - 1:04d}-12" if month == 1 else f"{year:04d}-{month - 1:02d}"


def save_period(
    frame: pd.DataFrame,
    source_name: str = "",
    file_hash: str = "",
    directory: Path | str | None = None,
) -> StoredPeriod:
    """Зберегти розібрану погодинну таблицю; наявний період перезаписується."""
    key = period_key_of(frame)
    path = _store_dir(directory) / f"{key}.parquet"
    frame.to_parquet(path, index=False, compression=COMPRESSION)

    entry = StoredPeriod(
        period_key=key,
        month_label=month_label_of(key),
        source_name=source_name,
        file_hash=file_hash,
        days=int(frame["date"].nunique()),
        hours=int(len(frame)),
        imported_at=datetime.now().isoformat(timespec="seconds"),
    )
    index = _read_index(directory)
    index[key] = entry
    _write_index(index, directory)
    return entry


def load_period(period_key: str, directory: Path | str | None = None) -> pd.DataFrame:
    """Прочитати збережену погодинну таблицю."""
    path = _store_dir(directory) / f"{period_key}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"У сховищі немає періоду {period_key}")
    frame = pd.read_parquet(path)
    # parquet зберігає дати як timestamp — повертаємо ті самі типи, що дає
    # читання xlsx, щоб round-trip був точним
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    if "timestamp" in frame.columns:
        frame["timestamp"] = frame["timestamp"].astype("datetime64[s]")
    return frame


def list_periods(directory: Path | str | None = None) -> list[StoredPeriod]:
    """Усі збережені періоди, найновіші першими."""
    index = _read_index(directory)
    existing = [
        entry
        for key, entry in index.items()
        if (_store_dir(directory) / f"{key}.parquet").exists()
    ]
    return sorted(existing, key=lambda e: e.period_key, reverse=True)


def get_period(period_key: str, directory: Path | str | None = None) -> StoredPeriod | None:
    return _read_index(directory).get(period_key)


def find_by_hash(file_hash: str, directory: Path | str | None = None) -> StoredPeriod | None:
    """Знайти вже збережений період за хешем вихідного файлу."""
    if not file_hash:
        return None
    for entry in list_periods(directory):
        if entry.file_hash == file_hash:
            return entry
    return None


def delete_period(period_key: str, directory: Path | str | None = None) -> bool:
    """Видалити період зі сховища."""
    index = _read_index(directory)
    removed = index.pop(period_key, None) is not None
    path = _store_dir(directory) / f"{period_key}.parquet"
    if path.exists():
        path.unlink()
        removed = True
    _write_index(index, directory)
    return removed


def comparison_candidate(
    period_key: str, directory: Path | str | None = None
) -> StoredPeriod | None:
    """Період для порівняння за замовчуванням — попередній місяць.

    Якщо саме попереднього місяця у сховищі немає, береться найближчий
    попередній із наявних; якщо раніших немає — ``None``.
    """
    available = {entry.period_key: entry for entry in list_periods(directory)}
    previous = previous_period_key(period_key)
    if previous in available:
        return available[previous]
    earlier = [key for key in available if key < period_key]
    return available[max(earlier)] if earlier else None
