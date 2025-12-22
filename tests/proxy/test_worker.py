import asyncio
import contextlib

import pytest
import zmq
from pytest_mock import MockerFixture

from mrok.proxy.asgi import ASGIAppWrapper
from mrok.proxy.datastructures import (
    DataTransferMetrics,
    Event,
    HTTPHeaders,
    HTTPRequest,
    HTTPResponse,
    ProcessMetrics,
    RequestsMetrics,
    ResponseTimeMetrics,
    Status,
    WorkerMetrics,
)
from mrok.proxy.middlewares import CaptureMiddleware, MetricsMiddleware
from mrok.proxy.worker import Worker
from tests.types import SettingsFactory


def test_setup_app(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_app = mocker.AsyncMock()
    worker = Worker(
        "my-worker-id",
        m_app,
        ziti_identity_file,
    )
    app = worker.setup_app()
    assert isinstance(app, ASGIAppWrapper)
    assert app.lifespan == worker.lifespan
    assert app.middlware[0].cls == MetricsMiddleware
    assert app.middlware[0].args[0] == worker._metrics_collector
    assert app.middlware[1].cls == CaptureMiddleware
    assert app.middlware[1].args[0] == worker.publish_response_event


def test_setup_app_events_disabled(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_app = mocker.AsyncMock()
    worker = Worker(
        "my-worker-id",
        m_app,
        ziti_identity_file,
        events_enabled=False,
    )
    app = worker.setup_app()
    assert isinstance(app, ASGIAppWrapper)
    assert app.lifespan is None

    assert app.middlware == []


def test_run(
    mocker: MockerFixture,
    ziti_identity_file: str,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.proxy.worker.get_settings", return_value=settings)
    m_setup_logging = mocker.patch("mrok.proxy.worker.setup_logging")

    m_mrokconfig = mocker.MagicMock()
    m_mrokconfig_ctor = mocker.patch(
        "mrok.proxy.worker.MrokBackendConfig", return_value=m_mrokconfig
    )

    m_server = mocker.MagicMock()
    m_server_ctor = mocker.patch("mrok.proxy.worker.MrokServer", return_value=m_server)
    m_app = mocker.MagicMock()
    mocker.patch.object(Worker, "setup_app", return_value=m_app)

    worker = Worker(
        "my-worker-id",
        m_app,
        ziti_identity_file,
    )
    worker.run()

    m_setup_logging.assert_called_once_with(settings)
    m_mrokconfig_ctor.assert_called_once_with(m_app, ziti_identity_file)
    m_server_ctor.assert_called_once_with(m_mrokconfig)
    m_server.run.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_app = mocker.AsyncMock()
    m_on_startup = mocker.patch.object(Worker, "on_startup")
    m_on_shutdown = mocker.patch.object(Worker, "on_shutdown")

    worker = Worker(
        "my-worker-id",
        m_app,
        ziti_identity_file,
    )

    async with worker.lifespan(m_app):
        pass

    m_on_startup.assert_awaited_once()
    m_on_shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_startup(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_publisher = mocker.MagicMock()
    m_zmq_ctx = mocker.MagicMock()
    m_zmq_ctx.socket.return_value = m_publisher
    m_zmq_ctx_ctor = mocker.MagicMock()
    m_zmq_ctx_ctor.return_value = m_zmq_ctx
    mocker.patch("mrok.proxy.worker.zmq.asyncio.Context", m_zmq_ctx_ctor)

    m_metrics = mocker.MagicMock()
    m_metricscollector_ctor = mocker.patch(
        "mrok.proxy.worker.WorkerMetricsCollector", return_value=m_metrics
    )
    m_publish_metrics_event = mocker.patch.object(Worker, "publish_metrics_event")

    m_app = mocker.AsyncMock()
    worker = Worker("my-worker-id", m_app, ziti_identity_file, events_publisher_port=8282)
    await worker.on_startup()
    m_metricscollector_ctor.assert_called_once_with("my-worker-id")
    assert worker._metrics_collector == m_metrics
    assert worker._zmq_ctx == m_zmq_ctx
    m_zmq_ctx.socket.assert_called_once_with(zmq.PUB)
    assert worker._events_publisher == m_publisher
    m_publisher.connect.assert_called_once_with("tcp://localhost:8282")
    await asyncio.sleep(0.001)
    m_publish_metrics_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_shutdown(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_app = mocker.AsyncMock()
    worker = Worker("my-worker-id", m_app, ziti_identity_file)

    async def my_coro():
        while True:
            await asyncio.sleep(5)

    task = asyncio.create_task(my_coro())

    worker._events_publish_task = task  # type: ignore
    worker._zmq_ctx = mocker.MagicMock()
    worker._events_publisher = mocker.MagicMock()

    await worker.on_shutdown()
    assert task.cancelled()
    worker._events_publisher.close.assert_called_once()  # type: ignore
    worker._zmq_ctx.term.assert_called_once()  # type: ignore


async def test_publish_metrics_event(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_app = mocker.AsyncMock()
    worker = Worker(
        "my-worker-id",
        m_app,
        ziti_identity_file,
    )

    metrics_snapshot = WorkerMetrics(
        worker_id="my-worker-id",
        data_transfer=DataTransferMetrics(
            bytes_in=1000,
            bytes_out=2000,
        ),
        requests=RequestsMetrics(rps=123, total=1000, successful=10, failed=30),
        response_time=ResponseTimeMetrics(
            avg=10,
            min=1,
            max=30,
            p50=11,
            p90=22,
            p99=11,
        ),
        process=ProcessMetrics(cpu=12, mem=22),
    )

    worker._metrics_collector = mocker.AsyncMock()
    worker._metrics_collector.snapshot.return_value = metrics_snapshot  # type: ignore
    worker._events_publisher = mocker.AsyncMock()

    task = asyncio.create_task(worker.publish_metrics_event())
    await asyncio.sleep(0.1)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    metrics_events = Event(
        type="status",
        data=Status(
            meta=worker._identity.mrok,
            metrics=metrics_snapshot,
        ),
    )
    worker._events_publisher.send_string.assert_called_once_with(metrics_events.model_dump_json())  # type: ignore


@pytest.mark.asyncio
async def test_publish_response_event(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_app = mocker.AsyncMock()
    worker = Worker(
        "my-worker-id",
        m_app,
        ziti_identity_file,
    )
    resp = HTTPResponse(
        type="response",
        headers=HTTPHeaders.from_asgi([(b"content-type", b"text/plain")]),
        request=HTTPRequest(
            method="GET",
            url="url",
            query_string=b"",
            headers=HTTPHeaders.from_asgi([(b"content-type", b"application/json")]),
            start_time=0,
        ),
        status=200,
        duration=20.5,
    )

    worker._events_publisher = mocker.AsyncMock()

    await worker.publish_response_event(resp)

    resp_event = Event(type="response", data=resp)

    worker._events_publisher.send_string.assert_awaited_once_with(resp_event.model_dump_json())  # type: ignore
