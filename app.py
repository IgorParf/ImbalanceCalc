"""Точка входу Streamlit-застосунку.

Запуск:  streamlit run app.py

Назви сторінок задаються тут явно через ``st.navigation``, тому імена файлів
залишаються англійськими, а в меню користувач бачить «Головна» та «Аналіз».
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Небаланси електричної енергії", page_icon="⚡", layout="wide")

navigation = st.navigation(
    [
        st.Page("views/home.py", title="Головна", icon="⚡", default=True),
        st.Page("views/analysis.py", title="Аналіз", icon="📊"),
    ]
)
navigation.run()
