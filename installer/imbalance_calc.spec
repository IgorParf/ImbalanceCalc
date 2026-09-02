# -*- mode: python ; coding: utf-8 -*-
"""Специфікація PyInstaller для ImbalanceCalc.

Збірка one-folder (не one-file): one-file щоразу розпаковує ~300 МБ у temp,
що дає старт понад 20 секунд і регулярні конфлікти з антивірусом.

Запуск:  pyinstaller installer/imbalance_calc.spec --noconfirm
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

ROOT = Path(SPECPATH).resolve().parent

# pathex додається лише під час створення Analysis(), тобто НИЖЧЕ. А
# collect_submodules() нижче має знайти пакет уже зараз, тому шлях до нього
# додаємо явно. Без цього collect_submodules поверне порожньо, збірка пройде
# без жодного попередження, а застосунок впаде на першій сторінці.
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

datas = []
binaries = []
hiddenimports = []

# Streamlit не працює без своїх фронтенд-асетів і без метаданих дистрибутиву:
# всередині він читає importlib.metadata.version("streamlit").
for package in ("streamlit", "pyarrow", "altair"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

for distribution in (
    "streamlit",
    "altair",
    "pandas",
    "numpy",
    "pyarrow",
    "matplotlib",
    "reportlab",
    "openpyxl",
    "xlsxwriter",
    "pywebview",
):
    datas += copy_metadata(distribution)

# Кириличний шрифт для PDF береться саме звідси — див. pdf_report._font_candidates()
datas += collect_data_files("matplotlib")

# Власні файли застосунку
datas += [
    (str(ROOT / "app.py"), "."),
    (str(ROOT / "views"), "views"),
    (str(ROOT / "data" / "samples"), "data/samples"),
    (str(ROOT / "docs" / "METHODOLOGY.md"), "docs"),
    (str(ROOT / ".streamlit"), ".streamlit"),
]

hiddenimports += ["streamlit.runtime.scriptrunner.magic_funcs"]

# Сторінки views/*.py лежать у збірці як ДАНІ, тому PyInstaller не бачить їхніх
# імпортів і сам знаходить лише ті модулі пакета, які тягне desktop/main.py.
# Без цього рядка застосунок запускається, але падає на першій же сторінці:
#     ModuleNotFoundError: No module named 'imbalance_calc.dataio'
package_modules = collect_submodules("imbalance_calc")
if len(package_modules) < 15:
    raise SystemExit(
        f"collect_submodules('imbalance_calc') повернув лише {len(package_modules)} "
        f"модулів: {package_modules}. Пакет не знайдено — перевірте sys.path у цьому "
        "файлі. Продовжувати не можна: збірка вийде неповною без жодної помилки."
    )
hiddenimports += package_modules

a = Analysis(
    [str(ROOT / "desktop" / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "pytest",
        "ruff",
        "mypy",
        "tkinter",
        "IPython",
        "jupyter",
        "notebook",
        "tests",
        # openpyxl працює й без lxml (відкат на ElementTree), а це 6,7 МБ
        "lxml",
        # Мережеві та RPC-можливості Arrow, яких застосунок не використовує:
        # він читає й пише локальні parquet-файли, не звертаючись нікуди.
        "pyarrow._flight",
        "pyarrow.flight",
        "pyarrow._substrait",
        "pyarrow.substrait",
        "pyarrow._s3fs",
        "pyarrow._gcsfs",
        "pyarrow._azurefs",
        "pyarrow._hdfs",
        "pyarrow._orc",
        "pyarrow.orc",
        "pyarrow._dataset_orc",
    ],
    noarchive=False,
)

# --- прибирання зайвого з дистрибутива ---------------------------------------
#
# collect_all("pyarrow") тягне все, що лежить у пакеті, включно з тим, що
# потрібне лише для компіляції C++-розширень або для невикористовуваних
# можливостей. На розмір це впливає відчутно: близько 30 МБ.
#
# Кожен запис нижче перевірений самоперевіркою (--selfcheck) і читанням
# реального parquet — див. installer/build.ps1.
DROP_SUFFIXES = (
    ".lib",   # статичні бібліотеки — лише для збірки розширень
    ".a",
    ".pdb",   # символи налагодження
)

#: Фрагменти шляху записуються через «/» — шлях нормалізується перед звіркою.
DROP_FRAGMENTS = (
    "pyarrow/include/",         # заголовки C++
    "pyarrow/src/",
    "pyarrow/tests/",
    "arrow_flight.dll",         # RPC-фреймворк Arrow Flight
    "arrow_python_flight.dll",
    "arrow_substrait.dll",      # серіалізація планів запитів
)


def _keep(destination: str) -> bool:
    normalized = destination.replace("\\", "/")
    if normalized.endswith(DROP_SUFFIXES):
        return False
    return not any(fragment in normalized for fragment in DROP_FRAGMENTS)


def _trim(entries, label):
    kept = [entry for entry in entries if _keep(entry[0])]
    dropped = len(entries) - len(kept)
    if dropped:
        print(f"[imbalance_calc] прибрано з {label}: {dropped} записів")
    return kept


a.binaries = _trim(a.binaries, "binaries")
a.datas = _trim(a.datas, "datas")

pyz = PYZ(a.pure)

version_file = ROOT / "installer" / "version_info.txt"

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImbalanceCalc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # без вікна консолі; діагностика — у %LOCALAPPDATA%\ImbalanceCalc\logs
    disable_windowed_traceback=False,
    icon=str(ROOT / "installer" / "app.ico")
    if (ROOT / "installer" / "app.ico").exists()
    else None,
    version=str(version_file) if version_file.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ImbalanceCalc",
)
