"""Тести шляхів: тека звітів, дані користувача, режим запакованого додатку."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from imbalance_calc import config


class TestDownloadsDir:
    """Тека звітів за замовчуванням — системна «Завантаження»."""

    def test_env_override_wins(self, monkeypatch, tmp_path):
        monkeypatch.setenv("IC_REPORTS_DIR", str(tmp_path))
        assert config.downloads_dir() == tmp_path

    def test_returns_existing_directory(self, monkeypatch):
        monkeypatch.delenv("IC_REPORTS_DIR", raising=False)
        path = config.downloads_dir()
        assert path.is_dir()

    @pytest.mark.skipif(sys.platform != "win32", reason="лише Windows")
    def test_matches_known_folder_api(self, monkeypatch):
        """Шлях беремо з SHGetKnownFolderPath, а не складаємо як ~/Downloads."""
        monkeypatch.delenv("IC_REPORTS_DIR", raising=False)
        known = config._known_folder(config._FOLDERID_DOWNLOADS)
        assert known is not None
        assert config.downloads_dir() == known

    @pytest.mark.skipif(sys.platform != "win32", reason="лише Windows")
    def test_falls_back_when_api_fails(self, monkeypatch):
        monkeypatch.delenv("IC_REPORTS_DIR", raising=False)
        monkeypatch.setattr(config, "_known_folder", lambda _: None)
        assert config.downloads_dir() in (Path.home() / "Downloads", Path.home())


class TestAppDataDir:
    def test_env_override_wins(self, monkeypatch, tmp_path):
        monkeypatch.setenv("IC_DATA_DIR", str(tmp_path))
        assert config.app_data_dir() == tmp_path

    def test_development_uses_repository(self, monkeypatch):
        monkeypatch.delenv("IC_DATA_DIR", raising=False)
        monkeypatch.setattr(config, "IS_FROZEN", False)
        assert config.app_data_dir() == config.resource_dir() / "data"

    def test_frozen_uses_localappdata(self, monkeypatch, tmp_path):
        """У запакованому додатку каталог встановлення лише для читання."""
        monkeypatch.delenv("IC_DATA_DIR", raising=False)
        monkeypatch.setattr(config, "IS_FROZEN", True)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert config.app_data_dir() == tmp_path / config.APP_NAME

    def test_frozen_without_localappdata(self, monkeypatch):
        monkeypatch.delenv("IC_DATA_DIR", raising=False)
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.setattr(config, "IS_FROZEN", True)
        assert config.app_data_dir() == Path.home() / config.APP_NAME


class TestResourceDir:
    def test_development_points_to_repository(self, monkeypatch):
        monkeypatch.setattr(config, "IS_FROZEN", False)
        assert (config.resource_dir() / "app.py").exists()

    def test_frozen_uses_meipass(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "IS_FROZEN", True)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        assert config.resource_dir() == tmp_path


class TestReportDestination:
    def test_reports_default_to_downloads(self):
        assert config.REPORTS_DIR == config.downloads_dir()

    def test_pdf_respects_explicit_directory(self, frame, tmp_path):
        from imbalance_calc.core import calculate_settlement
        from imbalance_calc.reporting import build_pdf_report

        path = build_pdf_report(calculate_settlement(frame), tmp_path)
        assert path.parent == tmp_path

    def test_pdf_uses_config_directory_when_omitted(self, frame, tmp_path, monkeypatch):
        from imbalance_calc.core import calculate_settlement
        from imbalance_calc.reporting import build_pdf_report

        monkeypatch.setattr(config, "REPORTS_DIR", tmp_path)
        path = build_pdf_report(calculate_settlement(frame))
        assert path.parent == tmp_path
