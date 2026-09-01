"""Димові тести сторінок Streamlit через streamlit.testing."""

from __future__ import annotations

from pathlib import Path

import pytest

from imbalance_calc.core import calculate_settlement
from imbalance_calc.ui.components import KEY_RESULT

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_main_page_renders_without_file():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    assert "Завантажте файл" in app.info[0].value


def test_analysis_page_requires_result():
    app = AppTest.from_file(str(ROOT / "pages" / "1_Аналіз.py"), default_timeout=60).run()
    assert not app.exception
    assert "Спочатку завантажте файл" in app.info[0].value


def test_analysis_page_renders_with_result(frame):
    app = AppTest.from_file(str(ROOT / "pages" / "1_Аналіз.py"), default_timeout=120)
    app.session_state[KEY_RESULT] = calculate_settlement(frame, source_name="test.xlsx")
    app.run()
    assert not app.exception
    assert any("липень 2026" in caption.value for caption in app.caption)
