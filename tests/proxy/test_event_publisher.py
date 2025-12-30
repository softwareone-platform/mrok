import asyncio
import contextlib

import pytest
import zmq
from pytest_mock import MockerFixture

from mrok.proxy.event_publisher import EventPublisher
from mrok.proxy.models import (
    DataTransferMetrics,
    Event,
    HTTPHeaders,
    HTTPRequest,
    HTTPResponse,
    Identity,
    ProcessMetrics,
    RequestsMetrics,
    ResponseTimeMetrics,
    Status,
    WorkerMetrics,
)


async def test_publish_metrics_event(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    identity = Identity.load_from_file(ziti_identity_file)
    event_publisher = EventPublisher(
        worker_id="my-worker-id",
        meta=identity.mrok,
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

    event_publisher._publisher = mocker.AsyncMock()
    event_publisher._metrics_collector = mocker.AsyncMock()
    event_publisher._metrics_collector.snapshot.return_value = metrics_snapshot  # type: ignore

    task = asyncio.create_task(event_publisher.publish_metrics_event())
    await asyncio.sleep(0.1)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    metrics_events = Event(
        type="status",
        data=Status(
            meta=identity.mrok,
            metrics=metrics_snapshot,
        ),
    )
    event_publisher._publisher.send_string.assert_called_once_with(  # type: ignore
        metrics_events.model_dump_json()
    )


@pytest.mark.asyncio
async def test_publish_response_event(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    identity = Identity.load_from_file(ziti_identity_file)
    event_publisher = EventPublisher(
        worker_id="my-worker-id",
        meta=identity.mrok,
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

    event_publisher._publisher = mocker.AsyncMock()

    await event_publisher.publish_response_event(resp)

    resp_event = Event(type="response", data=resp)
    event_publisher._publisher.send_string.assert_awaited_once_with(  # type: ignore
        resp_event.model_dump_json()
    )


@pytest.mark.asyncio
async def test_lifespan(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_on_startup = mocker.patch.object(EventPublisher, "on_startup")
    m_on_shutdown = mocker.patch.object(EventPublisher, "on_shutdown")

    identity = Identity.load_from_file(ziti_identity_file)
    event_publisher = EventPublisher(
        worker_id="my-worker-id",
        meta=identity.mrok,
    )

    m_app = mocker.AsyncMock()
    async with event_publisher.lifespan(m_app):
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
    mocker.patch("mrok.proxy.event_publisher.zmq.asyncio.Context", m_zmq_ctx_ctor)

    m_metrics = mocker.MagicMock()
    m_metricscollector_ctor = mocker.patch(
        "mrok.proxy.event_publisher.MetricsCollector", return_value=m_metrics
    )
    m_publish_metrics_event = mocker.patch.object(EventPublisher, "publish_metrics_event")

    identity = Identity.load_from_file(ziti_identity_file)
    event_publisher = EventPublisher(
        worker_id="my-worker-id",
        meta=identity.mrok,
        event_publisher_port=8282,
    )

    await event_publisher.on_startup()
    m_metricscollector_ctor.assert_called_once_with("my-worker-id")
    assert event_publisher._metrics_collector == m_metrics
    assert event_publisher._zmq_ctx == m_zmq_ctx
    m_zmq_ctx.socket.assert_called_once_with(zmq.PUB)
    m_publisher.connect.assert_called_once_with("tcp://localhost:8282")
    await asyncio.sleep(0.001)
    m_publish_metrics_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_shutdown(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    identity = Identity.load_from_file(ziti_identity_file)
    event_publisher = EventPublisher(
        worker_id="my-worker-id",
        meta=identity.mrok,
    )

    async def my_coro():
        while True:
            await asyncio.sleep(5)

    task = asyncio.create_task(my_coro())

    event_publisher._publish_task = task  # type: ignore
    event_publisher._publisher = mocker.MagicMock()
    event_publisher._zmq_ctx = mocker.MagicMock()

    await event_publisher.on_shutdown()
    assert task.cancelled()
    event_publisher._publisher.close.assert_called_once()  # type: ignore
    event_publisher._zmq_ctx.term.assert_called_once()  # type: ignore
