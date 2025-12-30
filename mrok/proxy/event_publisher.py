import asyncio
import contextlib
import logging

import zmq
import zmq.asyncio

from mrok.proxy.asgi import ASGIAppWrapper
from mrok.proxy.metrics import MetricsCollector
from mrok.proxy.middleware import CaptureMiddleware, MetricsMiddleware
from mrok.proxy.models import Event, HTTPResponse, ServiceMetadata, Status
from mrok.types.proxy import ASGIApp

logger = logging.getLogger("mrok.proxy")


class EventPublisher:
    def __init__(
        self,
        worker_id: str,
        meta: ServiceMetadata | None = None,
        event_publisher_port: int = 50000,
        metrics_interval: float = 5.0,
    ):
        self._worker_id = worker_id
        self._meta = meta
        self._metrics_interval = metrics_interval
        self.publisher_port = event_publisher_port
        self._zmq_ctx = zmq.asyncio.Context()
        self._publisher = self._zmq_ctx.socket(zmq.PUB)
        self._metrics_collector = MetricsCollector(self._worker_id)
        self._publish_task = None

    async def on_startup(self):
        self._publisher.connect(f"tcp://localhost:{self.publisher_port}")
        self._publish_task = asyncio.create_task(self.publish_metrics_event())
        logger.info(f"Events publishing for worker {self._worker_id} started")

    async def on_shutdown(self):
        self._publish_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._publish_task
        self._publisher.close()
        self._zmq_ctx.term()
        logger.info(f"Events publishing for worker {self._worker_id} stopped")

    async def publish_metrics_event(self):
        while True:
            snap = await self._metrics_collector.snapshot()
            event = Event(type="status", data=Status(meta=self._meta, metrics=snap))
            await self._publisher.send_string(event.model_dump_json())
            await asyncio.sleep(self._metrics_interval)

    async def publish_response_event(self, response: HTTPResponse):
        event = Event(type="response", data=response)
        await self._publisher.send_string(event.model_dump_json())  # type: ignore[attr-defined]

    def setup_middleware(self, app: ASGIAppWrapper):
        app.add_middleware(CaptureMiddleware, self.publish_response_event)
        app.add_middleware(MetricsMiddleware, self._metrics_collector)  # type: ignore

    @contextlib.asynccontextmanager
    async def lifespan(self, app: ASGIApp):
        await self.on_startup()  # type: ignore
        yield
        await self.on_shutdown()  # type: ignore
