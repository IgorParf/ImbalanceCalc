"""Запуск ImbalanceCalc у нативному вікні Windows.

Streamlit піднімається у фоновому потоці на локальному порту, а pywebview
показує його як звичайне вікно застосунку — без браузера й адресного рядка.

Запуск під час розробки:
    python desktop/main.py

У запакованому вигляді цей самий файл є точкою входу для PyInstaller.
"""

from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from imbalance_calc.config import APP_NAME, LOG_DIR, resource_dir  # noqa: E402
from imbalance_calc.ui.save_dialog import DESKTOP_ENV  # noqa: E402

WINDOW_TITLE = "Небаланси електричної енергії"
#: Розмір вікна, якщо розгортання на весь екран не спрацює.
WINDOW_SIZE = (1440, 900)
STARTUP_TIMEOUT = 60.0

#: Модулі, які потрібні сторінкам. Сторінки лежать у збірці як дані, тому
#: PyInstaller не бачить їхніх імпортів — перевіряємо явно (див. --selfcheck).
REQUIRED_MODULES = (
    "imbalance_calc",
    "imbalance_calc.config",
    "imbalance_calc.models",
    "imbalance_calc.store",
    "imbalance_calc.exceptions",
    "imbalance_calc.dataio",
    "imbalance_calc.dataio.loaders",
    "imbalance_calc.dataio.schema",
    "imbalance_calc.dataio.validators",
    "imbalance_calc.core",
    "imbalance_calc.core.methodology",
    "imbalance_calc.core.settlement",
    "imbalance_calc.core.daily",
    "imbalance_calc.reporting",
    "imbalance_calc.reporting.summary",
    "imbalance_calc.reporting.pdf_report",
    "imbalance_calc.reporting.excel_report",
    "imbalance_calc.ui.components",
    "imbalance_calc.ui.save_dialog",
    "streamlit",
    "altair",
    "pandas",
    "pyarrow",
    "webview",
)


def setup_logging() -> Path:
    """Без консолі помилки видно лише у файлі — тому лог обов'язковий."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "desktop.log"
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )
    return path


def free_port() -> int:
    """Вільний порт на локальному інтерфейсі."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def port_is_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def wait_for_server(port: int, timeout: float = STARTUP_TIMEOUT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_is_open(port):
            return True
        time.sleep(0.15)
    return False


def allow_signal_handlers_off_main_thread() -> None:
    """Дозволити Streamlit ставити обробники сигналів поза головним потоком.

    ``bootstrap.run()`` викликає ``signal.signal(SIGTERM, ...)`` для коректного
    завершення, а Python дозволяє це лише в головному потоці — інакше
    ``ValueError: signal only works in main thread``. Головний потік тут
    зайнятий вікном pywebview, тому обробник просто ігнорується: життєвим
    циклом застосунку керує закриття вікна, а не сигнал.

    У головному потоці ``signal.signal`` продовжує працювати як зазвичай.
    """
    import signal

    original = signal.signal

    def tolerant(signalnum, handler):  # noqa: ANN001, ANN202 — підпис як у stdlib
        try:
            return original(signalnum, handler)
        except ValueError:
            return None

    signal.signal = tolerant


def start_streamlit(port: int) -> threading.Thread:
    """Підняти Streamlit у фоновому потоці.

    Прив'язка саме до 127.0.0.1: назовні застосунок не слухає нічого.
    """
    from streamlit.web import bootstrap

    script = str(resource_dir() / "app.py")
    flags = {
        "server.address": "127.0.0.1",
        "server.port": port,
        "server.headless": True,
        "server.fileWatcherType": "none",
        "server.enableCORS": False,
        "server.enableXsrfProtection": False,
        "browser.gatherUsageStats": False,
        "global.developmentMode": False,
        "logger.level": "info",
    }

    def run() -> None:
        try:
            allow_signal_handlers_off_main_thread()
            bootstrap.load_config_options(flag_options=flags)
            bootstrap.run(script, False, [], flags)
        except Exception:
            logging.exception("Streamlit завершився з помилкою")

    thread = threading.Thread(target=run, name="streamlit", daemon=True)
    thread.start()
    return thread


def selfcheck() -> int:
    """Перевірити зібраний застосунок без відкривання вікна.

    Запуск ``ImbalanceCalc.exe --selfcheck`` імпортує всі модулі, потрібні
    сторінкам, і формує пробний PDF. Це ловить два класи проблем, які інакше
    видно лише при ручному клацанні по інтерфейсу:

    * відсутні у збірці модулі пакета (сторінки лежать як дані, тому
      PyInstaller не бачить їхніх імпортів);
    * відсутній кириличний шрифт для PDF.

    Результат пишеться в лог і повертається кодом виходу: 0 — усе гаразд.
    """
    import importlib

    problems: list[str] = []

    for name in REQUIRED_MODULES:
        try:
            importlib.import_module(name)
        except Exception as error:  # noqa: BLE001 — цікавить будь-яка причина
            problems.append(f"модуль {name}: {error}")

    if not problems:
        try:
            from imbalance_calc.reporting.pdf_report import _register_fonts

            _register_fonts()
        except Exception as error:  # noqa: BLE001
            problems.append(f"кириличний шрифт для PDF: {error}")

    for problem in problems:
        logging.error("Самоперевірка: %s", problem)
        print(f"ПОМИЛКА: {problem}", file=sys.stderr)

    if problems:
        logging.error("Самоперевірка провалена (%d проблем)", len(problems))
        return 1

    logging.info("Самоперевірка пройдена: %d модулів, шрифт PDF", len(REQUIRED_MODULES))
    print(f"OK: {len(REQUIRED_MODULES)} модулів, кириличний шрифт для PDF")
    return 0


def main() -> int:
    log_path = setup_logging()

    if "--selfcheck" in sys.argv:
        return selfcheck()

    logging.info("Старт %s", APP_NAME)
    os.environ[DESKTOP_ENV] = "1"

    port = free_port()
    start_streamlit(port)

    if not wait_for_server(port):
        logging.error("Streamlit не піднявся за %.0f с", STARTUP_TIMEOUT)
        print(
            f"Не вдалося запустити застосунок. Подробиці у файлі: {log_path}",
            file=sys.stderr,
        )
        return 1

    logging.info("Сервер на 127.0.0.1:%d", port)

    import webview

    webview.create_window(
        WINDOW_TITLE,
        f"http://127.0.0.1:{port}",
        width=WINDOW_SIZE[0],
        height=WINDOW_SIZE[1],
        min_size=(1024, 700),
        maximized=True,  # таблиці та графіки широкі — вікно відкриваємо розгорнутим
    )
    webview.start()
    logging.info("Вікно закрито, завершення")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
