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
    ],
    noarchive=False,
)

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
