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
    ):
        self._worker_id = worker_id
        self._identity_file = identity_file
        self._identity = Identity.load_from_file(self._identity_file)
        self._app = app

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

        config = BackendConfig(app, self._identity_file)
        server = Server(config)
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            server.run()
