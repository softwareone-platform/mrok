import logging
import os
import signal
import threading
from collections.abc import Callable
from pathlib import Path

from watchfiles import watch
from watchfiles.filters import PythonFilter
from watchfiles.run import CombinedProcess, start_process

logger = logging.getLogger("mrok.agent")


def print_path(path):
    try:
        return f'"{path.relative_to(Path.cwd())}"'
    except ValueError:
        return f'"{path}"'


class Master:
    def __init__(
        self,
        start_fn: Callable,
        workers: int,
        reload: bool,
    ):
        self.start_fn = start_fn
        self.workers = workers
        self.reload = reload
        self.worker_processes: list[CombinedProcess] = []
        self.stop_event = threading.Event()
        self.watch_filter = PythonFilter(ignore_paths=None)
        self.watcher = watch(
            Path.cwd(),
            watch_filter=self.watch_filter,
            stop_event=self.stop_event,
            yield_on_timeout=True,
        )
        self.setup_signals_handler()

    def setup_signals_handler(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self.handle_signal)

    def handle_signal(self, *args, **kwargs):
        self.stop_event.set()

    def start(self):
        for _ in range(self.workers):
            p = start_process(
                self.start_fn,
                "function",
                (),
                None,
            )
            logger.info(f"Worker [{p.pid}] started")
            self.worker_processes.append(p)

    def stop(self):
        for process in self.worker_processes:
            process.stop(sigint_timeout=5, sigkill_timeout=1)
        self.worker_processes = []

    def restart(self):
        self.stop()
        self.start()

    def __iter__(self):
        return self

    def __next__(self):
        changes = next(self.watcher)
        if changes:
            return list({Path(change[1]) for change in changes})
        return None

    def run(self):
        self.start()
        logger.info(f"Master process started: {os.getpid()}")
        if self.reload:
            for files_changed in self:
                if files_changed:
                    logger.warning(
                        f"{', '.join(map(print_path, files_changed))} changed, reloading...",
                    )
                    self.restart()
        else:
            self.stop_event.wait()
