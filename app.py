"""Точка входу Streamlit-застосунку.

Запуск у браузері:      streamlit run app.py
Запуск нативним вікном: python desktop/main.py

Назви сторінок задаються тут явно через ``st.navigation``, тому імена файлів
залишаються англійськими, а в меню користувач бачить «Головна» та «Аналіз».
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Небаланси електричної енергії", page_icon="⚡", layout="wide")

# Шляхи мають бути абсолютними: у запакованому додатку робочий каталог
# відрізняється від каталогу зі сторінками, і відносні шляхи не знаходяться.
_VIEWS = _ROOT / "views"

navigation = st.navigation(
    [
        st.Page(str(_VIEWS / "home.py"), title="Головна", icon="⚡", default=True),
        st.Page(str(_VIEWS / "analysis.py"), title="Аналіз", icon="📊"),
    ]
)
navigation.run()
