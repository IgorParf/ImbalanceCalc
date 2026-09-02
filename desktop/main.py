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
from imbalance_calc.console import prepare_console  # noqa: E402
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


def _check_data_formats() -> list[str]:
    """Перевірити формати, на яких тримається робота зі сховищем і файлами ГП.

    Зі збірки свідомо прибрано частину pyarrow (Flight, Substrait, заголовки)
    та lxml — див. installer/imbalance_calc.spec. Ці перевірки підтверджують,
    що прибрано лише зайве: parquet читається й пишеться, xlsx відкривається.
    """
    problems: list[str] = []

    try:
        import tempfile

        import pandas as pd

        frame = pd.DataFrame({"година": [1, 2], "обсяг": [1.5, -0.25]})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "check.parquet"
            frame.to_parquet(path, index=False, compression="zstd")
            restored = pd.read_parquet(path)
        if not restored.equals(frame):
            problems.append("parquet: прочитані дані не збігаються із записаними")
    except Exception as error:  # noqa: BLE001
        problems.append(f"parquet (сховище періодів): {error}")

    try:
        from imbalance_calc.config import SAMPLES_DIR
        from imbalance_calc.dataio import load_monthly_file

        samples = sorted(SAMPLES_DIR.glob("*.xlsx"))
        if samples:
            frame = load_monthly_file(samples[0])
            if frame.empty:
                problems.append("xlsx: зразок прочитано, але таблиця порожня")
    except Exception as error:  # noqa: BLE001
        problems.append(f"xlsx (читання файлу ГП): {error}")

    return problems


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
    started = time.monotonic()

    def stage(label: str) -> None:
        """Позначити етап у лозі: без цього незрозуміло, де саме затримка."""
        logging.info("Самоперевірка: %s (%.1f с)", label, time.monotonic() - started)

    for name in REQUIRED_MODULES:
        stage(f"імпорт {name}")
        try:
            importlib.import_module(name)
        except Exception as error:  # noqa: BLE001 — цікавить будь-яка причина
            problems.append(f"модуль {name}: {error}")

    if not problems:
        stage("шрифт для PDF")
        try:
            from imbalance_calc.reporting.pdf_report import _register_fonts

            _register_fonts()
        except Exception as error:  # noqa: BLE001
            problems.append(f"кириличний шрифт для PDF: {error}")

    if not problems:
        stage("parquet і xlsx")
        problems.extend(_check_data_formats())

    stage("завершено")

    for problem in problems:
        logging.error("Самоперевірка: %s", problem)
        print(f"ПОМИЛКА: {problem}", file=sys.stderr)

    if problems:
        logging.error("Самоперевірка провалена (%d проблем)", len(problems))
        return 1

    logging.info(
        "Самоперевірка пройдена: %d модулів, шрифт PDF, parquet, xlsx",
        len(REQUIRED_MODULES),
    )
    print(f"OK: {len(REQUIRED_MODULES)} модулів, шрифт PDF, parquet, xlsx")
    return 0


def main() -> int:
    prepare_console()
    log_path = setup_logging()

    if "--selfcheck" in sys.argv:
        code = selfcheck()
        # Імпорт важких бібліотек лишає живими сторонні недемонічні потоки, і
        # звичайний вихід чекав би на них. У GitHub Actions це проявилось як
        # зависання: перевірка відпрацювала за 2 секунди, а процес не
        # завершувався ще вісім хвилин, доки крок не обірвав таймаут.
        # Для одноразової діагностики примусовий вихід — правильна поведінка:
        # результат уже записано в журнал і повернуто кодом.
        logging.shutdown()
        os._exit(code)

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
