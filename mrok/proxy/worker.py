import asyncio
import contextlib
import logging
from pathlib import Path

from uvicorn.importer import import_from_string

from mrok.conf import get_settings
from mrok.logging import setup_logging
from mrok.proxy.asgi import ASGIAppWrapper
from mrok.proxy.event_publisher import EventPublisher
from mrok.proxy.models import Identity
from mrok.proxy.ziticorn import BackendConfig, Server
from mrok.types.proxy import ASGIApp

logger = logging.getLogger("mrok.proxy")


class Worker:
    def __init__(
        self,
        worker_id: str,
        app: ASGIApp | str,
        identity_file: str | Path,
        *,
        events_enabled: bool = True,
        event_publisher_port: int = 50000,
        metrics_interval: float = 5.0,
        ziti_load_timeout_ms: int = 5000,
        backlog: int = 2048,
        timeout_keep_alive: int = 5,
        limit_concurrency: int = None,
        limit_max_requests: int = None,
    ):
        self._worker_id = worker_id
        self._identity_file = identity_file
        self._identity = Identity.load_from_file(self._identity_file)
        self._app = app
        self._ziti_load_timeout_ms = ziti_load_timeout_ms
        self._backlog = backlog
        self._timeout_keep_alive = timeout_keep_alive
        self._limit_concurrency = limit_concurrency
        self._limit_max_requests = limit_max_requests

        self._events_enabled = events_enabled
        self._event_publisher = (
            EventPublisher(
                worker_id=worker_id,
                meta=self._identity.mrok,
                event_publisher_port=event_publisher_port,
                metrics_interval=metrics_interval,
            )
            if events_enabled
            else None
        )

    def setup_app(self):
        app = ASGIAppWrapper(
            self._app if not isinstance(self._app, str) else import_from_string(self._app),
            lifespan=self._event_publisher.lifespan if self._events_enabled else None,
        )

        if self._events_enabled:
            self._event_publisher.setup_middleware(app)
        return app

    def run(self):
        setup_logging(get_settings())
        app = self.setup_app()

        config = BackendConfig(
            app,
            self._identity_file,
            ziti_load_timeout_ms=self._ziti_load_timeout_ms,
            backlog=self._backlog,
            timeout_keep_alive=self._timeout_keep_alive,
            limit_concurrency=self._limit_concurrency,
            limit_max_requests=self._limit_max_requests,
        )
        server = Server(config)
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            server.run()
