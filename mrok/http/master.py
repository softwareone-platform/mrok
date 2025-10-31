import logging
import os
import signal
import threading
import time
from collections.abc import Callable
from pathlib import Path

from watchfiles import watch
from watchfiles.filters import PythonFilter
from watchfiles.run import CombinedProcess, start_process

logger = logging.getLogger("mrok.agent")

MONITOR_THREAD_JOIN_TIMEOUT = 5
MONITOR_THREAD_CHECK_DELAY = 1
MONITOR_THREAD_ERROR_DELAY = 3


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
        self.worker_processes: dict[int, CombinedProcess] = {}
        self.stop_event = threading.Event()
        self.watch_filter = PythonFilter(ignore_paths=None)
        self.watcher = watch(
            Path.cwd(),
            watch_filter=self.watch_filter,
            stop_event=self.stop_event,
            yield_on_timeout=True,
        )
        self.setup_signals_handler()
        self.monitor_thread = None

    def setup_signals_handler(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self.handle_signal)

    def handle_signal(self, *args, **kwargs):
        self.stop_event.set()

    def start_worker(self, worker_id: int):
        """Start a single worker process"""
        p = start_process(
            self.start_fn,
            "function",
            (),
            None,
        )
        logger.info(f"Worker {worker_id} [{p.pid}] started")
        return p

    def start(self):
        for i in range(self.workers):
            p = self.start_worker(i)
            self.worker_processes[i] = p

    def stop(self):
        for process in self.worker_processes.values():
            process.stop(sigint_timeout=5, sigkill_timeout=1)
        self.worker_processes.clear()

    def restart(self):
        self.stop()
        self.start()

    def monitor_workers(self):
        while not self.stop_event.is_set():
            try:
                for worker_id, process in self.worker_processes.items():
                    if not process.is_alive():
                        logger.warning(f"Worker {worker_id} [{process.pid}] died unexpectedly")
                        process.stop(sigint_timeout=1, sigkill_timeout=1)
                        new_process = self.start_worker(worker_id)
                        self.worker_processes[worker_id] = new_process
                        logger.info(
                            f"Restarted worker {worker_id} [{process.pid}] -> [{new_process.pid}]"
                        )

                time.sleep(MONITOR_THREAD_CHECK_DELAY)

            except Exception as e:
                logger.error(f"Error in worker monitoring: {e}")
                time.sleep(MONITOR_THREAD_ERROR_DELAY)

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

        # Start worker monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_workers, daemon=True)
        self.monitor_thread.start()
        logger.debug("Worker monitoring thread started")

        try:
            if self.reload:
                for files_changed in self:
                    if files_changed:
                        logger.warning(
                            f"{', '.join(map(print_path, files_changed))} changed, reloading...",
                        )
                        self.restart()
            else:
                self.stop_event.wait()
        finally:
            if self.monitor_thread and self.monitor_thread.is_alive():  # pragma: no cover
                logger.debug("Wait for monitor worker to exit")
                self.monitor_thread.join(timeout=MONITOR_THREAD_JOIN_TIMEOUT)
            self.stop()
