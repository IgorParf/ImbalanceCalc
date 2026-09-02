"""Тести підготовки консолі до кирилиці.

Це вже двічі ламало роботу: спершу самоперевірку запускача, потім генерацію
інструкції в GitHub Actions. Обидва рази — мовчазне падіння з
``UnicodeEncodeError`` на консолі cp1252/cp866. Тест нижче стежить, щоб кожна
точка входу, яка друкує текст, готувала консоль.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = sorted((ROOT / "scripts").glob("*.py"))


def _prints_text(path: Path) -> bool:
    """Чи є у файлі виклик print на рівні модуля або у функціях."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
        for node in ast.walk(tree)
    )


def test_scripts_exist():
    assert SCRIPTS, "не знайдено жодного скрипта у scripts/"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_printing_script_prepares_console(script):
    if not _prints_text(script):
        pytest.skip(f"{script.name} нічого не друкує")
    source = script.read_text(encoding="utf-8")
    assert "prepare_console" in source, (
        f"{script.name} друкує текст, але не викликає prepare_console() — "
        "у консолі cp1252/cp866 це впаде з UnicodeEncodeError"
    )


def test_launcher_prepares_console():
    source = (ROOT / "desktop" / "main.py").read_text(encoding="utf-8")
    assert "prepare_console()" in source


def test_workflows_set_encoding():
    """Другий шар захисту: змінна оточення на рівні workflow."""
    for name in ("tests.yml", "release.yml"):
        source = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "PYTHONIOENCODING: utf-8" in source, f"{name} без PYTHONIOENCODING"


def test_release_workflow_does_not_unpublish():
    """Повторний push тега не має повертати опублікований випуск у чернетки."""
    source = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "draft: true" not in source
