"""Тести діалогу збереження звіту."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from imbalance_calc.ui import save_dialog


@pytest.fixture
def desktop(monkeypatch):
    monkeypatch.setenv(save_dialog.DESKTOP_ENV, "1")


def _fake_webview(monkeypatch, answer):
    """Підставити модуль webview, що повертає заданий шлях із діалогу."""
    calls: dict[str, object] = {}

    class Window:
        def create_file_dialog(self, dialog_type, directory=None, save_filename=None):
            calls["type"] = dialog_type
            calls["directory"] = directory
            calls["filename"] = save_filename
            return answer

    module = types.SimpleNamespace(
        windows=[Window()],
        SAVE_DIALOG=30,
        FileDialog=types.SimpleNamespace(SAVE=30),
    )
    monkeypatch.setitem(sys.modules, "webview", module)
    return calls


class TestIsDesktop:
    def test_browser_by_default(self, monkeypatch):
        monkeypatch.delenv(save_dialog.DESKTOP_ENV, raising=False)
        assert not save_dialog.is_desktop()

    def test_desktop_when_flag_set(self, desktop):
        assert save_dialog.is_desktop()


class TestAskSavePath:
    def test_browser_mode_returns_none(self, monkeypatch):
        """У браузері нативного діалогу немає — там працює download_button."""
        monkeypatch.delenv(save_dialog.DESKTOP_ENV, raising=False)
        assert save_dialog.ask_save_path("report.pdf") is None

    def test_returns_chosen_path(self, desktop, monkeypatch, tmp_path):
        target = tmp_path / "report.pdf"
        _fake_webview(monkeypatch, str(target))
        assert save_dialog.ask_save_path("report.pdf") == target

    def test_defaults_to_downloads(self, desktop, monkeypatch, tmp_path):
        from imbalance_calc import config

        monkeypatch.setenv("IC_REPORTS_DIR", str(tmp_path))
        calls = _fake_webview(monkeypatch, str(tmp_path / "report.pdf"))
        save_dialog.ask_save_path("report.pdf")
        assert calls["directory"] == str(config.downloads_dir())
        assert calls["filename"] == "report.pdf"

    def test_cancelled_dialog_returns_none(self, desktop, monkeypatch):
        _fake_webview(monkeypatch, None)
        assert save_dialog.ask_save_path("report.pdf") is None

    def test_accepts_sequence_result(self, desktop, monkeypatch, tmp_path):
        target = tmp_path / "report.pdf"
        _fake_webview(monkeypatch, (str(target),))
        assert save_dialog.ask_save_path("report.pdf") == target


class TestSaveBytes:
    def test_writes_file(self, desktop, monkeypatch, tmp_path):
        target = tmp_path / "nested" / "report.pdf"
        _fake_webview(monkeypatch, str(target))
        path = save_dialog.save_bytes(b"%PDF-1.4", "report.pdf")
        assert path == target
        assert target.read_bytes() == b"%PDF-1.4"

    def test_cancelled_writes_nothing(self, desktop, monkeypatch, tmp_path):
        _fake_webview(monkeypatch, None)
        assert save_dialog.save_bytes(b"data", "report.pdf") is None
        assert list(tmp_path.iterdir()) == []

    def test_browser_mode_writes_nothing(self, monkeypatch):
        monkeypatch.delenv(save_dialog.DESKTOP_ENV, raising=False)
        assert save_dialog.save_bytes(b"data", "report.pdf") is None


class TestReveal:
    def test_handles_missing_startfile(self, monkeypatch, tmp_path):
        monkeypatch.delattr("os.startfile", raising=False)
        assert save_dialog.reveal(tmp_path) is False

    def test_opens_parent_of_file(self, monkeypatch, tmp_path):
        opened: list[Path] = []
        target = tmp_path / "report.pdf"
        target.write_bytes(b"x")
        monkeypatch.setattr("os.startfile", lambda p: opened.append(Path(p)), raising=False)
        assert save_dialog.reveal(target) is True
        assert opened == [tmp_path]
