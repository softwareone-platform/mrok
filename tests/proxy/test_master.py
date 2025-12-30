import signal
import threading
import time
from collections.abc import Generator
from pathlib import Path

import zmq
from pytest_mock import MockerFixture
from watchfiles import Change

from mrok.proxy.master import (
    MONITOR_THREAD_JOIN_TIMEOUT,
    MasterBase,
    start_events_router,
    start_uvicorn_worker,
)
from tests.conftest import SettingsFactory


def test_start_events_router_hook(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.proxy.master.get_settings", return_value=settings)
    m_setup_logging = mocker.patch("mrok.proxy.master.setup_logging")
    m_frontend = mocker.MagicMock()
    m_backend = mocker.MagicMock()
    m_zmq_ctx = mocker.MagicMock()
    m_zmq_ctx.socket.side_effect = [m_frontend, m_backend]
    m_zmq_ctx_ctor = mocker.MagicMock()
    m_zmq_ctx_ctor.return_value = m_zmq_ctx
    mocker.patch("mrok.proxy.master.zmq.Context", m_zmq_ctx_ctor)
    m_proxy = mocker.patch("mrok.proxy.master.zmq.proxy")

    start_events_router(5000, 5101)

    m_setup_logging.assert_called_once_with(settings)
    assert m_zmq_ctx.socket.mock_calls[0].args[0] == zmq.XSUB
    assert m_zmq_ctx.socket.mock_calls[1].args[0] == zmq.XPUB
    m_frontend.bind.assert_called_once_with("tcp://localhost:5000")
    m_backend.bind.assert_called_once_with("tcp://localhost:5101")
    m_proxy.assert_called_once_with(m_frontend, m_backend)
    m_frontend.close.assert_called_once()
    m_backend.close.assert_called_once()
    m_zmq_ctx.term.assert_called_once()


def test_start_uvicorn_worker_hook(
    mocker: MockerFixture,
):
    m_worker = mocker.MagicMock()
    m_worker_ctor = mocker.patch(
        "mrok.proxy.master.Worker",
        return_value=m_worker,
    )
    m_app = mocker.MagicMock()
    start_uvicorn_worker(
        "my-wk-id",
        m_app,
        "my-id-file.json",
        False,
        2233,
        24.0,
    )
    m_worker_ctor.assert_called_once_with(
        "my-wk-id",
        m_app,
        "my-id-file.json",
        events_enabled=False,
        event_publisher_port=2233,
        metrics_interval=24.0,
    )
    m_worker.run.assert_called_once()


def test_init(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    mocked_setup_signals = mocker.patch.object(Master, "setup_signals_handler")

    master = Master(
        "my-identity.json",
        workers=3,
        reload=True,
        events_enabled=False,
        events_pub_port=50000,
        events_sub_port=51000,
        metrics_interval=7.0,
    )
    assert master.identity_file == "my-identity.json"
    assert master.workers == 3
    assert master.reload is True
    assert master.events_enabled is False
    assert master.events_pub_port == 50000
    assert master.events_sub_port == 51000
    assert master.metrics_interval == 7.0
    mocked_setup_signals.assert_called_once()


def test_setup_signals_handler(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    mocked_signal = mocker.patch("mrok.proxy.master.signal.signal")
    master = Master("my-identity.json")
    assert mocked_signal.call_count == 2
    assert mocked_signal.mock_calls[0].args == (signal.SIGINT, master.handle_signal)
    assert mocked_signal.mock_calls[1].args == (signal.SIGTERM, master.handle_signal)


def test_handle_signal(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    master = Master("my-identity.json")
    assert master.stop_event.is_set() is False
    master.handle_signal()
    assert master.stop_event.is_set() is True


def test_start_worker(mocker: MockerFixture):
    m_asgi_app = mocker.AsyncMock()

    class Master(MasterBase):
        def get_asgi_app(self):
            return m_asgi_app

    m_proc = mocker.MagicMock()
    mocked_start_process = mocker.patch("mrok.proxy.master.start_process", return_value=m_proc)

    master = Master(
        "my-identity.json",
        workers=3,
        reload=False,
        events_enabled=True,
        events_pub_port=50000,
        events_sub_port=51000,
        metrics_interval=10,
    )
    assert master.start_worker("my-worker-id") == m_proc
    mocked_start_process.assert_called_once_with(
        start_uvicorn_worker,
        "function",
        (
            "my-worker-id",
            m_asgi_app,
            "my-identity.json",
            True,
            50000,
            10,
        ),
        None,
    )


def test_start_events_router(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    m_proc = mocker.MagicMock()
    mocked_start_process = mocker.patch("mrok.proxy.master.start_process", return_value=m_proc)

    master = Master(
        "my-identity.json",
        events_pub_port=50000,
        events_sub_port=51000,
    )
    master.start_events_router()
    assert master.zmq_pubsub_router_process == m_proc
    mocked_start_process.assert_called_once_with(
        start_events_router,
        "function",
        (50000, 51000),
        None,
    )


def test_start_workers(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    w0 = mocker.MagicMock()
    w1 = mocker.MagicMock()
    w2 = mocker.MagicMock()

    mocked_start_worker = mocker.patch.object(Master, "start_worker", side_effect=[w0, w1, w2])

    master = Master("my-identity.json", workers=3)
    master.start_workers()
    assert master.worker_processes[master.worker_identifiers[0]] == w0
    assert master.worker_processes[master.worker_identifiers[1]] == w1
    assert master.worker_processes[master.worker_identifiers[2]] == w2
    for i in range(3):
        assert mocked_start_worker.mock_calls[i].args[0] == master.worker_identifiers[i]


def test_start(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    mocked_start_events_router = mocker.patch.object(Master, "start_events_router")
    mocked_start_workers = mocker.patch.object(Master, "start_workers")
    mocked_monitor_thread = mocker.MagicMock()

    master = Master(
        "my-identity.json",
    )
    master.monitor_thread = mocked_monitor_thread
    master.start()
    mocked_start_events_router.assert_called_once()
    mocked_start_workers.assert_called_once()
    mocked_monitor_thread.start.assert_called_once()


def test_stop_workers(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    w0 = mocker.MagicMock()
    w1 = mocker.MagicMock()
    master = Master("my-identity.json")

    master.worker_processes = {"id1": w0, "id2": w1}
    master.stop_workers()
    w0.stop.assert_called_once_with(sigint_timeout=5, sigkill_timeout=1)
    w1.stop.assert_called_once_with(sigint_timeout=5, sigkill_timeout=1)
    assert master.worker_processes == {}


def test_stop_event_router(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    master = Master("my-identity.json")
    mocked_zmq_pubsub_router_process = mocker.MagicMock()
    master.zmq_pubsub_router_process = mocked_zmq_pubsub_router_process
    master.stop_events_router()
    mocked_zmq_pubsub_router_process.stop.assert_called_once_with(
        sigint_timeout=5, sigkill_timeout=1
    )


def test_stop(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    mocked_stop_events_router = mocker.patch.object(Master, "stop_events_router")
    mocked_stop_workers = mocker.patch.object(Master, "stop_workers")
    mocked_monitor_thread = mocker.MagicMock()
    mocked_monitor_thread.is_alive.return_value = True

    master = Master("my-identity.json")
    master.monitor_thread = mocked_monitor_thread
    master.stop()

    mocked_stop_events_router.assert_called_once()
    mocked_stop_workers.assert_called_once()
    mocked_monitor_thread.join.assert_called_once_with(timeout=MONITOR_THREAD_JOIN_TIMEOUT)


def test_restart(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    mocked_stop = mocker.patch.object(Master, "stop_workers")
    mocked_start = mocker.patch.object(Master, "start_workers")
    master = Master("my-identity.json")
    master.restart()
    mocked_stop.assert_called()
    mocked_start.assert_called()


def test_iter(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    master = Master("my-identity.json")
    assert iter(master) == master


def test_next(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    def watcher() -> Generator:
        yield {(Change.modified, "/file1.py")}
        yield None

    master = Master("my-identity.json")
    master.watcher = watcher()
    assert next(master) == [Path("/file1.py")]
    assert next(master) is None


def test_run(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    mocked_start = mocker.patch.object(Master, "start")
    mocked_stop = mocker.patch.object(Master, "stop")
    master = Master("my-identity.json")
    mocked_stop_event = mocker.MagicMock()
    master.stop_event = mocked_stop_event
    master.run()
    mocked_start.assert_called_once()
    mocked_stop_event.wait.assert_called_once()
    mocked_stop.assert_called_once()


def test_run_with_reload(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    mocker.patch.object(Master, "start")
    mocker.patch.object(Master, "stop")
    mocked_restart = mocker.patch.object(Master, "restart")

    def watcher() -> Generator:
        yield {(Change.modified, "/file1.py")}
        yield None

    master = Master("my-identity.json", reload=True)
    master.watcher = watcher()
    master.run()

    mocked_restart.assert_called_once()


def test_monitor_workers_restarts_dead_process(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    mocker.patch("mrok.proxy.master.MONITOR_THREAD_CHECK_DELAY", 0.1)

    mock_start_worker = mocker.patch.object(Master, "start_worker")
    master = Master("my-identity.json")

    dead_process = mocker.Mock()
    dead_process.is_alive.return_value = False
    dead_process.pid = 12345

    alive_process = mocker.Mock()
    alive_process.is_alive.return_value = True
    alive_process.pid = 12346

    new_process = mocker.Mock()
    new_process.pid = 12347

    master.worker_processes = {"id1": dead_process, "id2": alive_process}
    master.pause_event.set()

    mock_start_worker.return_value = new_process

    monitor_thread = threading.Thread(target=master.monitor_workers)
    monitor_thread.start()
    time.sleep(0.1)
    master.stop_event.set()
    monitor_thread.join()

    dead_process.stop.assert_called_once_with(sigint_timeout=1, sigkill_timeout=1)
    mock_start_worker.assert_called_once_with("id1")
    assert master.worker_processes["id1"] == new_process
    assert master.worker_processes["id2"] == alive_process


def test_monitor_workers_handles_is_alive_exception(mocker: MockerFixture):
    class Master(MasterBase):
        def get_asgi_app(self):
            return mocker.AsyncMock()

    mocker.patch("mrok.proxy.master.MONITOR_THREAD_ERROR_DELAY", 0.1)
    mock_logger = mocker.patch("mrok.proxy.master.logger.error")
    master = Master("my-identity.json")

    problematic_process = mocker.Mock()
    problematic_process.is_alive.side_effect = Exception("Test exception")

    master.worker_processes = {"id": problematic_process}
    master.pause_event.set()

    monitor_thread = threading.Thread(target=master.monitor_workers)
    monitor_thread.start()

    time.sleep(0.1)
    master.stop_event.set()
    monitor_thread.join()

    assert mock_logger.mock_calls[0].args[0] == "Error in worker monitoring: Test exception"
