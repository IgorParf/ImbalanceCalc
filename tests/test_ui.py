"""Димові тести сторінок Streamlit через streamlit.testing.

Сховище на час тестів підмінюється тимчасовим каталогом, щоб тести не бачили
реальні дані користувача і не залежали від того, що вже імпортовано.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from imbalance_calc import config, store
from imbalance_calc.ui.components import KEY_PERIOD, KEY_RESULT

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

ROOT = Path(__file__).resolve().parents[1]
HOME = str(ROOT / "views" / "home.py")
ANALYSIS = str(ROOT / "views" / "analysis.py")


@pytest.fixture
def empty_store(tmp_path, monkeypatch):
    """Порожнє сховище замість реального."""
    import streamlit as st

    monkeypatch.setattr(config, "STORE_DIR", tmp_path / "store")
    st.cache_data.clear()
    yield tmp_path / "store"
    st.cache_data.clear()


@pytest.fixture
def seeded_store(empty_store, frame):
    store.save_period(frame, "test.xlsx", "hash", directory=empty_store)
    return empty_store


def test_home_prompts_for_file_when_store_is_empty(empty_store):
    app = AppTest.from_file(HOME, default_timeout=60).run()
    assert not app.exception
    assert any("Сховище порожнє" in info.value for info in app.info)


def test_home_renders_stored_period_without_upload(seeded_store):
    """Ключова властивість: розрахунок відкривається без завантаження файлу."""
    app = AppTest.from_file(HOME, default_timeout=120).run()
    assert not app.exception
    assert app.session_state[KEY_RESULT].period_key == "2026-07"
    labels = [metric.label for metric in app.metric]
    assert "Платіж без ПДВ, грн" in labels
    assert "Всього з ПДВ, грн" in labels
    assert "Всього обмеження, год.хв" in labels
    assert "Всього обмежено виробіток, МВт·год" in labels


def test_analysis_requires_selected_period(empty_store):
    app = AppTest.from_file(ANALYSIS, default_timeout=60).run()
    assert not app.exception
    assert any("Спочатку оберіть період" in info.value for info in app.info)


def test_analysis_renders_with_result(seeded_store, frame):
    from imbalance_calc.core import calculate_settlement

    app = AppTest.from_file(ANALYSIS, default_timeout=120)
    app.session_state[KEY_RESULT] = calculate_settlement(frame, source_name="test.xlsx")
    app.session_state[KEY_PERIOD] = "2026-07"
    app.run()
    assert not app.exception
    assert any("липень 2026" in caption.value for caption in app.caption)


def test_analysis_defaults_to_previous_month(seeded_store, frame):
    """Порівняння за замовчуванням має підставляти попередній місяць."""
    from imbalance_calc.core import calculate_settlement

    june = frame.copy()
    june["date"] = june["date"].map(lambda d: d.replace(month=6))
    store.save_period(june, "june.xlsx", "hash-june", directory=seeded_store)

    app = AppTest.from_file(ANALYSIS, default_timeout=120)
    app.session_state[KEY_RESULT] = calculate_settlement(frame, source_name="test.xlsx")
    app.session_state[KEY_PERIOD] = "2026-07"
    app.run()
    assert not app.exception
    selectboxes = [box for box in app.selectbox if box.label == "Період для порівняння"]
    assert selectboxes and selectboxes[0].value == "2026-06"
