import asyncio
import contextlib
import logging
import os
import signal
import threading
from collections.abc import Callable
from configparser import RawConfigParser
from pathlib import Path
from typing import IO, Any

from uvicorn.config import (
    LOGGING_CONFIG,
    ASGIApplication,
    Config,
    HTTPProtocolType,
    InterfaceType,
    LifespanType,
    WSProtocolType,
)
from uvicorn.server import Server
from watchfiles import watch
from watchfiles.filters import PythonFilter
from watchfiles.run import CombinedProcess, start_process

logger = logging.getLogger("uvicorn.error")


def print_path(path):
    try:
        return f'"{path.relative_to(Path.cwd())}"'
    except ValueError:
        return f'"{path}"'


def start_server(config: Config, service_name, identity_file):
    import openziti

    openziti.monkeypatch(
        bindings={(config.host, config.port): {"ztx": identity_file, "service": service_name}}
    )
    config.configure_logging()
    server = Server(config)
    with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
        server.run()


class Master:
    def __init__(self, config: Config, service_name, identity_file, reload):
        self.config = config
        self.service_name = service_name
        self.identity_file = identity_file
        self.reload = reload
        self.workers: list[CombinedProcess] = []
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
        for _ in range(self.config.workers):
            self.start_worker_process(self.config, self.service_name, self.identity_file)

    def start_worker_process(self, config, service_name, identity_file):
        p = start_process(
            start_server,
            "function",
            (config, service_name, identity_file),
            {},
        )

        self.workers.append(p)

    def stop(self):
        for process in self.workers:
            process.stop(sigint_timeout=5, sigkill_timeout=1)
        self.workers = []

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


def run(
    app: ASGIApplication | Callable[..., Any] | str,
    service_name: str,
    identity_file: str | os.PathLike[str],
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    workers: int = 4,
    reload: bool = True,
    http: type[asyncio.Protocol] | HTTPProtocolType = "auto",
    ws: type[asyncio.Protocol] | WSProtocolType = "auto",
    ws_max_size: int = 16777216,
    ws_max_queue: int = 32,
    ws_ping_interval: float | None = 20.0,
    ws_ping_timeout: float | None = 20.0,
    ws_per_message_deflate: bool = True,
    lifespan: LifespanType = "auto",
    interface: InterfaceType = "auto",
    env_file: str | os.PathLike[str] | None = None,
    log_config: dict[str, Any] | str | RawConfigParser | IO[Any] | None = LOGGING_CONFIG,
    log_level: str | int | None = None,
    access_log: bool = True,
    proxy_headers: bool = True,
    server_header: bool = True,
    date_header: bool = True,
    forwarded_allow_ips: list[str] | str | None = None,
    root_path: str = "",
    limit_concurrency: int | None = None,
    backlog: int = 2048,
    limit_max_requests: int | None = None,
    timeout_keep_alive: int = 5,
    timeout_graceful_shutdown: int | None = None,
    headers: list[tuple[str, str]] | None = None,
    use_colors: bool | None = None,
    factory: bool = False,
    h11_max_incomplete_event_size: int | None = None,
) -> None:
    config = Config(
        app,
        host=host,
        port=port,
        http=http,
        ws=ws,
        workers=workers,
        ws_max_size=ws_max_size,
        ws_max_queue=ws_max_queue,
        ws_ping_interval=ws_ping_interval,
        ws_ping_timeout=ws_ping_timeout,
        ws_per_message_deflate=ws_per_message_deflate,
        lifespan=lifespan,
        interface=interface,
        env_file=env_file,
        log_config=log_config,
        log_level=log_level,
        access_log=access_log,
        proxy_headers=proxy_headers,
        server_header=server_header,
        date_header=date_header,
        forwarded_allow_ips=forwarded_allow_ips,
        root_path=root_path,
        limit_concurrency=limit_concurrency,
        backlog=backlog,
        limit_max_requests=limit_max_requests,
        timeout_keep_alive=timeout_keep_alive,
        timeout_graceful_shutdown=timeout_graceful_shutdown,
        headers=headers,
        use_colors=use_colors,
        factory=factory,
        h11_max_incomplete_event_size=h11_max_incomplete_event_size,
        loop="asyncio",
    )

    master = Master(config, service_name, identity_file, reload)
    master.run()
