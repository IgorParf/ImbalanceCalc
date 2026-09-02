"""Константи, шляхи та налаштування розрахунку.

Шляхи розрізняють два режими роботи:

* **розробка** — запуск із репозиторію, дані лежать у `data/` поруч з кодом;
* **запакований додаток** (PyInstaller) — ресурси програми доступні лише для
  читання, тому дані користувача переносяться у ``%LOCALAPPDATA%``.

Параметри розрахунку (K_e, alpha, K_im, ПДВ), яких немає у файлі ГП,
описані в docs/METHODOLOGY.md, розділ 9.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "ImbalanceCalc"

#: Чи працюємо всередині збірки PyInstaller.
IS_FROZEN = bool(getattr(sys, "frozen", False))

#: GUID системної теки «Завантаження» (FOLDERID_Downloads).
_FOLDERID_DOWNLOADS = "{374DE290-123F-4565-9164-39C4925E467B}"


def _known_folder(folder_id: str) -> Path | None:
    """Шлях до системної теки Windows за її GUID.

    Читати реєстр або складати ``~/Downloads`` ненадійно: користувач міг
    перенести теку на інший диск. Правильна відповідь — у SHGetKnownFolderPath.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        guid = _GUID()
        ole32 = ctypes.windll.ole32
        if ole32.CLSIDFromString(ctypes.c_wchar_p(folder_id), ctypes.byref(guid)) != 0:
            return None

        pointer = ctypes.c_wchar_p()
        result = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(guid), 0, None, ctypes.byref(pointer)
        )
        if result != 0 or not pointer.value:
            return None
        try:
            return Path(pointer.value)
        finally:
            ole32.CoTaskMemFree(pointer)
    except (OSError, AttributeError, ImportError):
        return None


def downloads_dir() -> Path:
    """Системна тека «Завантаження» — стартова тека діалогу збереження звіту."""
    override = os.getenv("IC_REPORTS_DIR")
    if override:
        return Path(override)

    known = _known_folder(_FOLDERID_DOWNLOADS)
    if known is not None and known.exists():
        return known

    candidate = Path.home() / "Downloads"
    return candidate if candidate.exists() else Path.home()


def resource_dir() -> Path:
    """Каталог з файлами, що постачаються разом із програмою (лише читання)."""
    if IS_FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def app_data_dir() -> Path:
    """Каталог даних користувача (сховище, вхідні файли, логи).

    У запакованому додатку каталог встановлення доступний лише для читання,
    тому дані живуть у ``%LOCALAPPDATA%\\ImbalanceCalc``.
    """
    override = os.getenv("IC_DATA_DIR")
    if override:
        return Path(override)
    if IS_FROZEN:
        base = os.getenv("LOCALAPPDATA")
        return (Path(base) if base else Path.home()) / APP_NAME
    return resource_dir() / "data"


BASE_DIR = resource_dir()
DATA_DIR = app_data_dir()
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
STORE_DIR = Path(os.getenv("IC_STORE_DIR", DATA_DIR / "store"))
LOG_DIR = DATA_DIR / "logs"

#: Зразки постачаються разом із програмою, а не лежать у даних користувача.
SAMPLES_DIR = BASE_DIR / "data" / "samples"

#: Тека, яку діалог збереження звіту пропонує за замовчуванням.
REPORTS_DIR = downloads_dir()

#: Поріг, вище якого доба потрапляє в окремий аналіз, грн (без ПДВ).
DAILY_ALERT_THRESHOLD_UAH = float(os.getenv("IC_DAILY_THRESHOLD", "10000"))

#: Допустиме відхилення K_e для типу генерації ВДЕ, %.
DEFAULT_K_E = float(os.getenv("IC_K_E", "5"))

#: Частка відшкодування вартості врегулювання небалансу alpha_e, %.
DEFAULT_ALPHA = float(os.getenv("IC_ALPHA", "100"))

#: Коефіцієнт ціни небалансу K_im за Правилами ринку (частка, не відсотки).
#: Значення 0,05 звірене з реально виставленим рахунком — див. розділ 13
#: docs/METHODOLOGY.md.
DEFAULT_K_IM = float(os.getenv("IC_K_IM", "0.05"))

#: Ставка ПДВ (частка).
DEFAULT_VAT_RATE = float(os.getenv("IC_VAT_RATE", "0.20"))

#: Округлення при виводі.
MONEY_ROUNDING = 2
VOLUME_ROUNDING = 6


@dataclass(frozen=True)
class CalculationSettings:
    """Параметри одного прогону розрахунку."""

    k_e: float = DEFAULT_K_E
    alpha: float = DEFAULT_ALPHA
    k_im: float = DEFAULT_K_IM
    vat_rate: float = DEFAULT_VAT_RATE
    daily_threshold_uah: float = DAILY_ALERT_THRESHOLD_UAH

    def describe(self) -> str:
        """Короткий опис параметрів для звіту."""
        threshold = f"{self.daily_threshold_uah:,.0f}".replace(",", " ")
        return (
            f"K_e = {self.k_e:g} %, "
            f"alpha = {self.alpha:g} %, "
            f"K_im = {self.k_im:g}, "
            f"ПДВ = {self.vat_rate * 100:g} %, "
            f"поріг доби = {threshold} грн"
        )
