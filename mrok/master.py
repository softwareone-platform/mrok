import asyncio
import contextlib
import json
import logging
import os
import signal
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

import zmq
import zmq.asyncio
from uvicorn.importer import import_from_string
from watchfiles import watch
from watchfiles.filters import PythonFilter
from watchfiles.run import CombinedProcess, start_process

from mrok.conf import get_settings
from mrok.datastructures import Event, HTTPResponse, Meta, Status
from mrok.http.config import MrokBackendConfig
from mrok.http.lifespan import LifespanWrapper
from mrok.http.middlewares import CaptureMiddleware, MetricsMiddleware
from mrok.http.server import MrokServer
from mrok.http.types import ASGIApp
from mrok.logging import setup_logging
from mrok.metrics import WorkerMetricsCollector

logger = logging.getLogger("mrok.agent")

MONITOR_THREAD_JOIN_TIMEOUT = 5
MONITOR_THREAD_CHECK_DELAY = 1
MONITOR_THREAD_ERROR_DELAY = 3


def print_path(path):
    try:
        return f'"{path.relative_to(Path.cwd())}"'
    except ValueError:
        return f'"{path}"'


def start_events_router(events_pub_port: int, events_sub_port: int):
    setup_logging(get_settings())
    context = zmq.Context()
    frontend = context.socket(zmq.XSUB)
    frontend.bind(f"tcp://localhost:{events_pub_port}")
    backend = context.socket(zmq.XPUB)
    backend.bind(f"tcp://localhost:{events_sub_port}")

    try:
        logger.info(f"Events router process started: {os.getpid()}")
        zmq.proxy(frontend, backend)
    except KeyboardInterrupt:
        pass
    finally:
        frontend.close()
        backend.close()
        context.term()


def start_uvicorn_worker(
    worker_id: str,
    app: ASGIApp,
    identity_file: str,
    events_pub_port: int,
    metrics_interval: float = 5.0,
):
    import sys

    sys.path.insert(0, os.getcwd())
    if isinstance(app, str):
        app = import_from_string(app)

    setup_logging(get_settings())
    identity = json.load(open(identity_file))
    meta = Meta(**identity["mrok"])
    ctx = zmq.asyncio.Context()
    pub = ctx.socket(zmq.PUB)
    pub.connect(f"tcp://localhost:{events_pub_port}")
    metrics = WorkerMetricsCollector(worker_id)

    task = None

    async def status_sender():
        while True:
            snap = await metrics.snapshot()
            event = Event(type="status", data=Status(meta=meta, metrics=snap))
            await pub.send_string(event.model_dump_json())
            await asyncio.sleep(metrics_interval)

    async def on_startup():  # noqa
        nonlocal task
        task = asyncio.create_task(status_sender())

    async def on_shutdown():  # noqa
        if task:
            task.cancel()

    async def on_response_complete(response: HTTPResponse):
        event = Event(type="response", data=response)
        await pub.send_string(event.model_dump_json())

    config = MrokBackendConfig(
        LifespanWrapper(
            MetricsMiddleware(
                CaptureMiddleware(
                    app,
                    on_response_complete,
                ),
                metrics,
            ),
            on_startup=on_startup,
            on_shutdown=on_shutdown,
        ),
        identity_file,
    )
    server = MrokServer(config)
    with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
        server.run()


class MasterBase(ABC):
    def __init__(
        self,
        identity_file: str,
        workers: int,
        reload: bool,
        events_pub_port: int,
        events_sub_port: int,
        metrics_interval: float = 5.0,
    ):
        self.identity_file = identity_file
        self.workers = workers
        self.reload = reload
        self.events_pub_port = events_pub_port
        self.events_sub_port = events_sub_port
        self.metrics_interval = metrics_interval
        self.worker_identifiers = [str(uuid4()) for _ in range(workers)]
        self.worker_processes: dict[str, CombinedProcess] = {}
        self.zmq_pubsub_router_process = None
        self.monitor_thread = threading.Thread(target=self.monitor_workers, daemon=True)
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.watch_filter = PythonFilter(ignore_paths=None)
        self.watcher = watch(
            Path.cwd(),
            watch_filter=self.watch_filter,
            stop_event=self.stop_event,
            yield_on_timeout=True,
        )
        self.setup_signals_handler()

    @abstractmethod
    def get_asgi_app(self):
        pass

    def setup_signals_handler(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self.handle_signal)

    def handle_signal(self, *args, **kwargs):
        self.stop_event.set()

    def start_worker(self, worker_id: str):
        """Start a single worker process"""

        p = start_process(
            start_uvicorn_worker,
            "function",
            (
                worker_id,
                self.get_asgi_app(),
                self.identity_file,
                self.events_pub_port,
                self.metrics_interval,
            ),
            None,
        )
        logger.info(f"Worker {worker_id} [{p.pid}] started")
        return p

    def start(self):
        self.start_events_router()
        self.start_workers()
        self.monitor_thread.start()

    def stop(self):
        if self.monitor_thread.is_alive():
            logger.debug("Wait for monitor worker to exit")
            self.monitor_thread.join(timeout=MONITOR_THREAD_JOIN_TIMEOUT)
        self.stop_workers()
        self.stop_events_router()

    def start_events_router(self):
        self.zmq_pubsub_router_process = start_process(
            start_events_router,
            "function",
            (
                self.events_pub_port,
                self.events_sub_port,
            ),
            None,
        )

    def stop_events_router(self):
        self.zmq_pubsub_router_process.stop(sigint_timeout=5, sigkill_timeout=1)

    def start_workers(self):
        for i in range(self.workers):
            worker_id = self.worker_identifiers[i]
            p = self.start_worker(worker_id)
            self.worker_processes[worker_id] = p

    def stop_workers(self):
        for process in self.worker_processes.values():
            if process.is_alive():
                process.stop(sigint_timeout=5, sigkill_timeout=1)
        self.worker_processes.clear()

    def restart(self):
        self.pause_event.set()
        self.stop_workers()
        self.start_workers()
        self.pause_event.clear()

    def monitor_workers(self):
        while not self.stop_event.is_set():
            try:
                self.pause_event.wait()
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
        setup_logging(get_settings())
        logger.info(f"Master process started: {os.getpid()}")
        self.start()
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
            self.stop()
