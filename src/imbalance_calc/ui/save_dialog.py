"""Збереження сформованого звіту з вибором теки користувачем.

Поведінка залежить від того, як запущено інтерфейс:

* **нативне вікно** (``desktop/main.py``, pywebview) — відкривається системний
  діалог «Зберегти як» зі стартовою текою «Завантаження»;
* **браузер** (``streamlit run app.py``) — нативний діалог показати неможливо,
  бо сторінка виконується на боці клієнта; там ту саму роль виконує
  ``st.download_button``: браузер кладе файл у свою теку завантажень або, якщо
  ввімкнено «Завжди питати, куди зберігати», показує власний діалог вибору.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..config import downloads_dir

#: Змінна, якою ``desktop/main.py`` позначає запуск у нативному вікні.
DESKTOP_ENV = "IC_DESKTOP"


def is_desktop() -> bool:
    """Чи працює інтерфейс у нативному вікні (а не у браузері)."""
    return os.getenv(DESKTOP_ENV) == "1"


def ask_save_path(suggested_name: str, directory: Path | str | None = None) -> Path | None:
    """Показати системний діалог «Зберегти як».

    Повертає обраний шлях або ``None``, якщо користувач скасував діалог чи
    нативне вікно недоступне. Стартова тека за замовчуванням — «Завантаження».
    """
    if not is_desktop():
        return None
    try:
        import webview
    except ImportError:
        return None

    windows = getattr(webview, "windows", None)
    if not windows:
        return None

    # pywebview 6 перейшов на FileDialog.SAVE; старий SAVE_DIALOG ще працює,
    # але вже попереджає про видалення
    dialog_type = getattr(getattr(webview, "FileDialog", None), "SAVE", None)
    if dialog_type is None:
        dialog_type = webview.SAVE_DIALOG

    start_dir = Path(directory) if directory else downloads_dir()
    result = windows[0].create_file_dialog(
        dialog_type,
        directory=str(start_dir),
        save_filename=suggested_name,
    )
    if not result:
        return None
    # pywebview повертає рядок для SAVE_DIALOG і послідовність для інших типів
    return Path(result[0] if isinstance(result, (list, tuple)) else result)


def save_bytes(
    data: bytes, suggested_name: str, directory: Path | str | None = None
) -> Path | None:
    """Запитати шлях і записати файл; ``None`` — користувач скасував діалог."""
    path = ask_save_path(suggested_name, directory)
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def reveal(path: Path | str) -> bool:
    """Відкрити теку з файлом у Провіднику. ``False``, якщо не вдалося."""
    target = Path(path)
    folder = target.parent if target.is_file() else target
    try:
        os.startfile(folder)  # noqa: S606 — штатний спосіб відкрити теку у Windows
        return True
    except (OSError, AttributeError):
        return False
