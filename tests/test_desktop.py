"""Тести запускача нативного вікна (без відкриття самого вікна)."""

from __future__ import annotations

import socket

import pytest

from desktop import main as desktop
from imbalance_calc import console


class TestPorts:
    def test_free_port_is_usable(self):
        port = desktop.free_port()
        assert 1024 < port < 65536
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", port))  # порт справді вільний

    def test_port_is_open_detects_listener(self):
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            port = server.getsockname()[1]
            assert desktop.port_is_open(port)

    def test_port_is_open_false_when_closed(self):
        assert not desktop.port_is_open(desktop.free_port())

    def test_wait_for_server_times_out(self):
        assert not desktop.wait_for_server(desktop.free_port(), timeout=0.3)

    def test_wait_for_server_succeeds(self):
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            assert desktop.wait_for_server(server.getsockname()[1], timeout=2.0)


class TestConsoleEncoding:
    """Кирилиця у виводі не має валити запуск у cp866/cp1252."""

    def test_reconfigures_streams(self, monkeypatch):
        calls: list[dict] = []

        class Stream:
            def reconfigure(self, **kwargs):
                calls.append(kwargs)

        monkeypatch.setattr(console.sys, "stdout", Stream())
        monkeypatch.setattr(console.sys, "stderr", Stream())
        console.prepare_console()
        assert calls == [{"encoding": "utf-8", "errors": "replace"}] * 2

    def test_survives_missing_streams(self, monkeypatch):
        """У вікні без консолі sys.stdout дорівнює None."""
        monkeypatch.setattr(console.sys, "stdout", None)
        monkeypatch.setattr(console.sys, "stderr", None)
        console.prepare_console()

    def test_survives_stream_without_reconfigure(self, monkeypatch):
        monkeypatch.setattr(console.sys, "stdout", object())
        monkeypatch.setattr(console.sys, "stderr", object())
        console.prepare_console()

    def test_survives_reconfigure_failure(self, monkeypatch):
        class Stream:
            def reconfigure(self, **kwargs):
                raise OSError("потік не підтримує зміну кодування")

        monkeypatch.setattr(console.sys, "stdout", Stream())
        monkeypatch.setattr(console.sys, "stderr", Stream())
        console.prepare_console()


class TestSignalShim:
    """Streamlit ставить обробник SIGTERM, а це можливо лише в головному потоці."""

    def test_signal_in_worker_thread_does_not_raise(self, monkeypatch):
        import signal
        import threading

        monkeypatch.setattr(signal, "signal", signal.signal)  # відкотиться після тесту
        desktop.allow_signal_handlers_off_main_thread()

        failure: list[BaseException] = []

        def worker() -> None:
            try:
                signal.signal(signal.SIGTERM, lambda *_: None)
            except BaseException as error:  # noqa: BLE001 — фіксуємо будь-яку
                failure.append(error)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        assert not failure

    def test_main_thread_still_registers_handlers(self, monkeypatch):
        import signal

        monkeypatch.setattr(signal, "signal", signal.signal)
        desktop.allow_signal_handlers_off_main_thread()

        previous = signal.getsignal(signal.SIGTERM)
        try:
            handler = lambda *_: None  # noqa: E731
            signal.signal(signal.SIGTERM, handler)
            assert signal.getsignal(signal.SIGTERM) is handler
        finally:
            signal.signal(signal.SIGTERM, previous)


class TestEntryPoint:
    def test_serves_only_loopback(self):
        """Назовні застосунок не слухає нічого."""
        source = (desktop.__file__ and open(desktop.__file__, encoding="utf-8").read()) or ""
        assert '"server.address": "127.0.0.1"' in source
        assert "0.0.0.0" not in source

    def test_app_script_exists(self):
        from imbalance_calc.config import resource_dir

        assert (resource_dir() / "app.py").exists()

    def test_logging_creates_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(desktop, "LOG_DIR", tmp_path / "logs")
        path = desktop.setup_logging()
        assert path.parent.exists()
        assert path.name == "desktop.log"


@pytest.mark.parametrize(
    "flag",
    [
        "server.headless",
        "server.fileWatcherType",
        "global.developmentMode",
        "browser.gatherUsageStats",
    ],
)
def test_required_flags_present(flag):
    source = open(desktop.__file__, encoding="utf-8").read()
    assert f'"{flag}"' in source
