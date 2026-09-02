"""Підготовка консолі до виводу кирилиці.

Кодування ``stdout`` залежить від того, звідки запущено програму: cmd.exe дає
cp866, Windows-runner GitHub Actions — cp1252. У жодному з них кирилиця не
представляється, тож звичайний ``print`` з українським текстом падає з
``UnicodeEncodeError`` — причому ще до того, як користувач побачить саме
повідомлення. На цьому вже двічі спіткнулися: у запускачі та в скриптах
генерації.

Тому кожна точка входу, яка щось друкує, викликає :func:`prepare_console`
першим рядком.
"""

from __future__ import annotations

import sys


def prepare_console() -> None:
    """Перевести ``stdout`` і ``stderr`` на UTF-8.

    Помилки кодування замінюються, а не спричиняють виняток: краще показати
    зіпсований символ, ніж обірвати роботу.

    У вікні без консолі ``sys.stdout`` дорівнює ``None`` — тоді робити нічого
    не треба, ``print`` там і так мовчить.
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
