import asyncio
import contextlib
import logging
from pathlib import Path

from uvicorn.importer import import_from_string

from mrok.conf import get_settings
from mrok.logging import setup_logging
from mrok.proxy.asgi import ASGIAppWrapper
from mrok.proxy.events import EventsPublisher
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
        ziti_load_timeout_ms: int = 5000,
        server_backlog: int = 2048,
        server_timeout_keep_alive: int = 5,
        server_limit_concurrency: int | None = None,
        server_limit_max_requests: int | None = None,
        events_enabled: bool = True,
        events_publisher_port: int = 50000,
        events_metrics_collect_interval: float = 5.0,
    ):
        self._worker_id = worker_id
        self._identity_file = identity_file
        self._identity = Identity.load_from_file(self._identity_file)
        self._app = app
        self._ziti_load_timeout_ms = ziti_load_timeout_ms
        self._server_backlog = server_backlog
        self._server_timeout_keep_alive = server_timeout_keep_alive
        self._server_limit_concurrency = server_limit_concurrency
        self._server_limit_max_requests = server_limit_max_requests

        self._events_enabled = events_enabled
        self._event_publisher = (
            EventsPublisher(
                worker_id=worker_id,
                meta=self._identity.mrok,
                events_publisher_port=events_publisher_port,
                events_metrics_collect_interval=events_metrics_collect_interval,
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
            backlog=self._server_backlog,
            timeout_keep_alive=self._server_timeout_keep_alive,
            limit_concurrency=self._server_limit_concurrency,
            limit_max_requests=self._server_limit_max_requests,
        )
        server = Server(config)
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            server.run()
