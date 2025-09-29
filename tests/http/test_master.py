import signal
from collections.abc import Generator
from pathlib import Path

from pytest_mock import MockerFixture
from watchfiles import Change

from mrok.http.master import Master


def test_init(mocker: MockerFixture):
    mocked_setup_signals = mocker.patch.object(Master, "setup_signals_handler")
    mocked_start_fn = mocker.MagicMock()
    master = Master(mocked_start_fn, 3, False)
    assert master.start_fn == mocked_start_fn
    assert master.workers == 3
    assert master.reload is False
    mocked_setup_signals.assert_called_once()


def test_setup_signals_handler(mocker: MockerFixture):
    mocked_signal = mocker.patch("mrok.http.master.signal.signal")
    master = Master(mocker.MagicMock(), 3, False)
    assert mocked_signal.call_count == 2
    assert mocked_signal.mock_calls[0].args == (signal.SIGINT, master.handle_signal)
    assert mocked_signal.mock_calls[1].args == (signal.SIGTERM, master.handle_signal)


def test_handle_signal(mocker: MockerFixture):
    master = Master(mocker.MagicMock(), 3, False)
    assert master.stop_event.is_set() is False
    master.handle_signal()
    assert master.stop_event.is_set() is True


def test_start(mocker: MockerFixture):
    processes = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
    mocked_start_process = mocker.patch(
        "mrok.http.master.start_process",
        side_effect=processes,
    )
    start_fn = mocker.MagicMock()
    master = Master(start_fn, 3, False)
    master.start()
    assert master.worker_processes == processes
    for i in range(3):
        assert mocked_start_process.mock_calls[i].args == (start_fn, "function", (), None)


def test_stop(mocker: MockerFixture):
    master = Master(mocker.MagicMock(), 3, False)
    p1 = mocker.MagicMock()
    p2 = mocker.MagicMock()
    master.worker_processes = [p1, p2]
    master.stop()
    p1.stop.assert_called_once_with(sigint_timeout=5, sigkill_timeout=1)
    p2.stop.assert_called_once_with(sigint_timeout=5, sigkill_timeout=1)


def test_restart(mocker: MockerFixture):
    mocked_stop = mocker.patch.object(Master, "stop")
    mocked_start = mocker.patch.object(Master, "start")
    master = Master(mocker.MagicMock(), 3, False)
    master.restart()
    mocked_stop.assert_called()
    mocked_start.assert_called()


def test_iter(mocker: MockerFixture):
    master = Master(mocker.MagicMock(), 3, False)
    assert iter(master) == master


def test_next(mocker: MockerFixture):
    def watcher() -> Generator:
        yield {(Change.modified, "/file1.py")}
        yield None

    master = Master(mocker.MagicMock(), 3, False)
    master.watcher = watcher()
    assert next(master) == [Path("/file1.py")]
    assert next(master) is None


def test_run(mocker: MockerFixture):
    mocked_start = mocker.patch.object(Master, "start")
    master = Master(mocker.MagicMock(), 3, False)
    mocked_stop_event = mocker.MagicMock()
    master.stop_event = mocked_stop_event
    master.run()
    mocked_start.assert_called_once()
    mocked_stop_event.wait.assert_called_once()


def test_run_with_reload(mocker: MockerFixture):
    mocker.patch.object(Master, "start")
    mocked_restart = mocker.patch.object(Master, "restart")

    def watcher() -> Generator:
        yield {(Change.modified, "/file1.py")}
        yield None

    master = Master(mocker.MagicMock(), 3, True)
    master.watcher = watcher()
    master.run()

    mocked_restart.assert_called_once()
