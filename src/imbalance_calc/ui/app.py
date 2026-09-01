"""Головна сторінка Streamlit-застосунку.

Запуск:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Розрахунок небалансів", layout="wide")
    st.title("Розрахунок платежу за небаланси електричної енергії")

    # TODO: завантаження файлу -> валідація -> розрахунок -> підсумки ->
    #       аналіз по добах -> доби понад 10 000 грн -> вивантаження звіту.
    st.info("Інтерфейс у розробці.")


if __name__ == "__main__":
    main()
