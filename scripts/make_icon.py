"""Створити іконку застосунку installer/app.ico.

Запуск:  python scripts/make_icon.py

Малюємо блискавку геометрично, а не символом зі шрифту: у шрифтах гліф ⚡
виглядає по-різному, а в .ico потрібен передбачуваний результат у кожному
з розмірів (16…256 px).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SIZES = (16, 24, 32, 48, 64, 128, 256)
BACKGROUND = (31, 78, 121)   # #1f4e79 — акцентний колір звітів і графіків
BOLT = (255, 209, 102)       # тепла жовта блискавка

#: Контур блискавки в частках від сторони квадрата.
BOLT_SHAPE = (
    (0.56, 0.08),
    (0.28, 0.54),
    (0.46, 0.54),
    (0.40, 0.92),
    (0.72, 0.44),
    (0.53, 0.44),
)


def draw(size: int) -> Image.Image:
    """Намалювати іконку заданого розміру зі згладжуванням."""
    scale = 8 if size <= 64 else 4
    canvas = size * scale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    painter = ImageDraw.Draw(image)

    radius = int(canvas * 0.22)
    painter.rounded_rectangle(
        (0, 0, canvas - 1, canvas - 1), radius=radius, fill=BACKGROUND
    )
    painter.polygon([(x * canvas, y * canvas) for x, y in BOLT_SHAPE], fill=BOLT)

    return image.resize((size, size), Image.LANCZOS)


def save(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    images = [draw(size) for size in SIZES]
    images[-1].save(path, format="ICO", sizes=[(s, s) for s in SIZES], append_images=images)
    return path


if __name__ == "__main__":
    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "installer" / "app.ico"
    )
    print(f"Іконку збережено: {save(target)}")
