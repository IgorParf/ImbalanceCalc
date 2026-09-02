"""Тести повноти збірки.

Сторінки ``views/*.py`` потрапляють у збірку як **дані**, тому PyInstaller не
аналізує їхніх імпортів і сам знаходить лише ті модулі пакета, які тягне
``desktop/main.py``. Через це застосунок запускався, але падав на першій
сторінці з ``ModuleNotFoundError: No module named 'imbalance_calc.dataio'``.

Тести нижче фіксують обидва запобіжники: явний перелік модулів для
самоперевірки та ``collect_submodules`` у специфікації.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from desktop.main import REQUIRED_MODULES

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "views"
SPEC = ROOT / "installer" / "imbalance_calc.spec"


def _imported_modules(path: Path) -> set[str]:
    """Модулі пакета, які імпортує сторінка."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return {name for name in found if name.split(".")[0] == "imbalance_calc"}


def _view_files() -> list[Path]:
    return sorted(VIEWS.glob("*.py"))


def test_views_exist():
    assert _view_files(), "не знайдено жодної сторінки у views/"


@pytest.mark.parametrize("view", _view_files(), ids=lambda p: p.name)
def test_view_imports_are_declared(view):
    """Кожен імпорт сторінки має бути в REQUIRED_MODULES самоперевірки."""
    missing = _imported_modules(view) - set(REQUIRED_MODULES)
    assert not missing, (
        f"{view.name} імпортує {sorted(missing)}, яких немає в REQUIRED_MODULES — "
        "самоперевірка збірки їх не помітить"
    )


def test_required_modules_are_importable():
    for name in REQUIRED_MODULES:
        importlib.import_module(name)


def test_spec_collects_all_submodules():
    """Без collect_submodules у збірку потрапляє лише частина пакета."""
    source = SPEC.read_text(encoding="utf-8")
    assert 'collect_submodules("imbalance_calc")' in source


def test_collect_submodules_covers_required():
    collect_submodules = pytest.importorskip(
        "PyInstaller.utils.hooks"
    ).collect_submodules
    collected = set(collect_submodules("imbalance_calc"))
    package_modules = {n for n in REQUIRED_MODULES if n.startswith("imbalance_calc")}
    assert package_modules <= collected


def test_app_entry_uses_absolute_page_paths():
    """Відносні шляхи ламаються у збірці: робочий каталог інший."""
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'st.Page("views/' not in source
    assert "_VIEWS" in source
