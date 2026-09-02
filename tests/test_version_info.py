"""Тести ресурсу версії для .exe.

Помилка тут не падає й нічого не друкує: Windows просто показує порожні
властивості файлу. Саме на це вже наступали, тому перевірки нижче фіксують
формат, а не лише факт генерації.
"""

from __future__ import annotations

import re

import pytest

from imbalance_calc import __version__
from scripts import make_version_info


@pytest.fixture
def text() -> str:
    return make_version_info.build()


class TestLanguageIdentifier:
    """StringTable і Translation мають вказувати на ту саму мову."""

    def test_identifiers_match(self, text):
        table = re.search(r"StringTable\(\s*'([0-9A-Fa-f]{8})'", text)
        translation = re.search(r"VarStruct\('Translation', \[(\d+), (\d+)\]\)", text)
        assert table and translation

        table_lang = int(table.group(1)[:4], 16)
        translation_lang = int(translation.group(1))
        assert table_lang == translation_lang, (
            "Ідентифікатор мови у StringTable не збігається з Translation — "
            "Windows не знайде таблицю і покаже порожні властивості файлу"
        )

    def test_uses_unicode_codepage(self, text):
        translation = re.search(r"VarStruct\('Translation', \[\d+, (\d+)\]\)", text)
        assert translation and int(translation.group(1)) == 1200


class TestContent:
    def test_version_matches_package(self, text):
        assert f"StringStruct('FileVersion', '{__version__}')" in text
        assert f"StringStruct('ProductVersion', '{__version__}')" in text

    def test_numeric_version_matches(self, text):
        major, minor, patch = (int(part) for part in __version__.split(".")[:3])
        assert f"filevers=({major}, {minor}, {patch}, 0)" in text
        assert f"prodvers=({major}, {minor}, {patch}, 0)" in text

    def test_describes_the_application(self, text):
        assert "ImbalanceCalc" in text
        assert "небаланси" in text.lower()

    @pytest.mark.parametrize("short_version", ["1", "2.3"])
    def test_pads_short_versions(self, short_version):
        built = make_version_info.build(short_version)
        assert "filevers=(" in built
        assert built.count(", 0)") >= 1


class TestParsing:
    def test_pyinstaller_can_parse(self, tmp_path):
        """Головна перевірка: ресурс має розбиратися самим PyInstaller-ом."""
        versioninfo = pytest.importorskip("PyInstaller.utils.win32.versioninfo")
        path = make_version_info.save(tmp_path / "version_info.txt")
        assert versioninfo.load_version_info_from_text_file(str(path)) is not None
