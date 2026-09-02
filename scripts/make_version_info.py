"""Створити ресурс версії installer/version_info.txt для PyInstaller.

Запуск:  python scripts/make_version_info.py

Windows показує ці дані у властивостях файлу та в діалозі UAC. Версія береться
з ``imbalance_calc.__version__``, щоб не розходилася з pyproject.toml.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from imbalance_calc import __version__  # noqa: E402
from imbalance_calc.console import prepare_console  # noqa: E402

COMPANY = "IgorParf"
PRODUCT = "ImbalanceCalc"
DESCRIPTION = "Розрахунок платежу за небаланси електричної енергії"
EXE_NAME = "ImbalanceCalc.exe"

TEMPLATE = """\
# Згенеровано scripts/make_version_info.py — не редагувати вручну.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', '{company}'),
         StringStruct('FileDescription', '{description}'),
         StringStruct('FileVersion', '{version}'),
         StringStruct('InternalName', '{product}'),
         StringStruct('LegalCopyright', '{company}'),
         StringStruct('OriginalFilename', '{exe}'),
         StringStruct('ProductName', '{product}'),
         StringStruct('ProductVersion', '{version}')])
    ]),
    # Ідентифікатор мови у StringTable ('0409') і в Translation (1033) мають
    # збігатися, інакше Windows не знаходить таблицю і показує порожні
    # властивості файлу. 1200 — кодова сторінка Unicode, тому текст може бути
    # українським незалежно від ідентифікатора мови.
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def build(version: str = __version__) -> str:
    parts = [int(piece) for piece in version.split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts
    return TEMPLATE.format(
        major=major,
        minor=minor,
        patch=patch,
        version=version,
        company=COMPANY,
        product=PRODUCT,
        description=DESCRIPTION,
        exe=EXE_NAME,
    )


def save(path: Path, version: str = __version__) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build(version), encoding="utf-8")
    return path


if __name__ == "__main__":
    prepare_console()
    target = Path(__file__).resolve().parents[1] / "installer" / "version_info.txt"
    print(f"Версію {__version__} записано: {save(target)}")
