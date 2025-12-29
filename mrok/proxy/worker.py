import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import zmq
import zmq.asyncio
from uvicorn.importer import import_from_string

from mrok.conf import get_settings
from mrok.logging import setup_logging
from mrok.proxy.asgi import ASGIAppWrapper
from mrok.proxy.config import MrokBackendConfig
from mrok.proxy.datastructures import Event, HTTPResponse, Status, ZitiIdentity
from mrok.proxy.metrics import WorkerMetricsCollector
from mrok.proxy.middlewares import CaptureMiddleware, MetricsMiddleware
from mrok.proxy.server import MrokServer
from mrok.proxy.types import ASGIApp

logger = logging.getLogger("mrok.proxy")


class Worker:
    def __init__(
        self,
        worker_id: str,
        app: ASGIApp | str,
        identity_file: str | Path,
        *,
        events_enabled: bool = True,
        events_publisher_port: int = 50000,
        metrics_interval: float = 5.0,
    ):
        self._worker_id = worker_id
        self._identity_file = identity_file
        self._identity = ZitiIdentity.load_from_file(self._identity_file)
        self._app = app
        self._events_enabled = events_enabled
        self._metrics_interval = metrics_interval
        self.events_publisher_port = events_publisher_port
        self._metrics_collector = WorkerMetricsCollector(self._worker_id)
        self._zmq_ctx = zmq.asyncio.Context()
        self._events_publisher = self._zmq_ctx.socket(zmq.PUB)
        self._events_publish_task = None

    async def on_startup(self):
        self._events_publisher.connect(f"tcp://localhost:{self.events_publisher_port}")
        self._events_publish_task = asyncio.create_task(self.publish_metrics_event())
        logger.info(f"Events publishing for worker {self._worker_id} started")

    async def on_shutdown(self):
        self._events_publish_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._events_publish_task
        self._events_publisher.close()
        self._zmq_ctx.term()
        logger.info(f"Events publishing for worker {self._worker_id} stopped")

    @asynccontextmanager
    async def lifespan(self, app: ASGIApp):
        await self.on_startup()
        yield
        await self.on_shutdown()

    async def publish_metrics_event(self):
        while True:
            snap = await self._metrics_collector.snapshot()
            event = Event(type="status", data=Status(meta=self._identity.mrok, metrics=snap))
            await self._events_publisher.send_string(event.model_dump_json())
            await asyncio.sleep(self._metrics_interval)

    async def publish_response_event(self, response: HTTPResponse):
        event = Event(type="response", data=response)
        await self._events_publisher.send_string(event.model_dump_json())  # type: ignore[attr-defined]

    def setup_app(self):
        app = ASGIAppWrapper(
            self._app if not isinstance(self._app, str) else import_from_string(self._app),
            lifespan=self.lifespan if self._events_enabled else None,
        )

        if self._events_enabled:
            app.add_middleware(CaptureMiddleware, self.publish_response_event)
            app.add_middleware(MetricsMiddleware, self._metrics_collector)

        return app

    def run(self):
        setup_logging(get_settings())
        app = self.setup_app()

        config = MrokBackendConfig(app, self._identity_file)
        server = MrokServer(config)
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            server.run()
