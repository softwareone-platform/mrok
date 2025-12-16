import asyncio

import pytest
from pytest_mock import MockerFixture

from mrok.proxy.datastructures import HTTPResponse
from mrok.proxy.middlewares import CaptureMiddleware, LifespanMiddleware, MetricsMiddleware
from mrok.proxy.types import Message
from tests.types import ReceiveFactory, SendFactory


@pytest.mark.asyncio
async def test_lifespan_events(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
):
    m_app = mocker.AsyncMock()
    m_on_startup = mocker.AsyncMock()
    m_on_shutdown = mocker.AsyncMock()

    sent: list[Message] = []
    receive = receive_factory([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])
    send = send_factory(sent)

    middleware = LifespanMiddleware(m_app, on_startup=m_on_startup, on_shutdown=m_on_shutdown)

    await middleware({"type": "lifespan"}, receive, send)
    assert sent == [
        {"type": "lifespan.startup.complete"},
        {"type": "lifespan.shutdown.complete"},
    ]
    m_on_startup.assert_awaited_once()
    m_on_shutdown.assert_awaited_once()
    m_app.assert_not_awaited()


@pytest.mark.asyncio
async def test_lifespan_invoke_app(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
):
    m_app = mocker.AsyncMock()
    m_on_startup = mocker.AsyncMock()
    m_on_shutdown = mocker.AsyncMock()

    receive = receive_factory()
    m_send = mocker.AsyncMock()

    middleware = LifespanMiddleware(m_app, on_startup=m_on_startup, on_shutdown=m_on_shutdown)

    await middleware({"type": "http"}, receive, m_send)
    m_on_startup.assert_not_awaited()
    m_on_shutdown.assert_not_awaited()
    m_app.assert_awaited_once_with({"type": "http"}, receive, m_send)


@pytest.mark.asyncio
async def test_metrics(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
):
    class MockApp:
        async def __call__(self, scope, receive, send):
            await receive()
            await receive()
            await send({"type": "http.response.start", "status": 200})
            await send({"type": "http.response.body", "body": b"OK", "more_body": True})
            await send({"type": "http.response.body", "body": b"Mrok!", "more_body": False})

    m_app = MockApp()

    m_metrics = mocker.AsyncMock()
    m_metrics.on_request_start.return_value = 100

    sent: list[Message] = []
    receive = receive_factory(
        [
            {"type": "http.request", "body": b"Who are", "more_body": True},
            {"type": "http.request", "body": b"You!", "more_body": False},
        ]
    )
    send = send_factory(sent)

    middleware = MetricsMiddleware(m_app, m_metrics)
    await middleware({"type": "http"}, receive, send)

    m_metrics.on_request_start.assert_awaited_once_with({"type": "http"})
    assert m_metrics.on_request_body.mock_calls[0].args[0] == len(b"Who are")
    assert m_metrics.on_request_body.mock_calls[1].args[0] == len(b"You!")
    m_metrics.on_response_start.assert_awaited_once_with(200)
    assert m_metrics.on_response_chunk.mock_calls[0].args[0] == len(b"OK")
    assert m_metrics.on_response_chunk.mock_calls[1].args[0] == len(b"Mrok!")
    m_metrics.on_request_end.assert_awaited_once_with(100, 200)


@pytest.mark.asyncio
async def test_metrics_lifespan(
    mocker: MockerFixture,
):
    m_app = mocker.AsyncMock()
    m_metrics = mocker.AsyncMock()
    m_receive = mocker.AsyncMock()
    m_send = mocker.AsyncMock()

    middleware = MetricsMiddleware(m_app, m_metrics)
    await middleware({"type": "lifespan"}, m_receive, m_send)
    m_app.assert_awaited_once_with({"type": "lifespan"}, m_receive, m_send)


@pytest.mark.asyncio
async def test_capture(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
):
    mocker.patch("mrok.proxy.middlewares.time.time", side_effect=[7, 25])

    class MockApp:
        async def __call__(self, scope, receive, send):
            await receive()
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send({"type": "http.response.body", "body": b"OK", "more_body": True})
            await send({"type": "http.response.body", "body": b"Mrok!", "more_body": False})

    m_app = MockApp()

    m_metrics = mocker.AsyncMock()
    m_metrics.on_request_start.return_value = 100

    sent: list[Message] = []
    receive = receive_factory(
        [
            {"type": "http.request", "body": b'{"my": "json"}', "more_body": False},
        ]
    )
    send = send_factory(sent)

    scope = {
        "type": "http",
        "method": "POST",
        "raw_path": b"/foo",
        "path": "/foo",
        "query_string": b"param=value",
        "headers": [(b"content-type", b"application/json")],
        "scheme": "https",
        "client": ("127.0.0.1", 12345),
        "server": ("localhost", 8000),
    }

    received_response: HTTPResponse | None = None

    async def on_response_complete(response: HTTPResponse):
        nonlocal received_response
        await asyncio.sleep(0)
        received_response = response

    middleware = CaptureMiddleware(m_app, on_response_complete)
    await middleware(scope, receive, send)
    await asyncio.sleep(0.1)

    assert received_response is not None
    assert received_response.request.method == "POST"
    assert received_response.request.url == "/foo"
    assert received_response.request.headers["content-type"] == "application/json"
    assert received_response.request.query_string == b"param=value"
    assert received_response.request.body == b'{"my": "json"}'
    assert received_response.status == 200
    assert received_response.headers["content-type"] == "text/plain"
    assert received_response.body == b"OKMrok!"
    assert received_response.duration == 18


@pytest.mark.asyncio
async def test_capture_lifespan(
    mocker: MockerFixture,
):
    m_app = mocker.AsyncMock()
    m_response_callback = mocker.AsyncMock()
    m_receive = mocker.AsyncMock()
    m_send = mocker.AsyncMock()

    middleware = CaptureMiddleware(m_app, m_response_callback)
    await middleware({"type": "lifespan"}, m_receive, m_send)
    m_app.assert_awaited_once_with({"type": "lifespan"}, m_receive, m_send)
    m_response_callback.assert_not_awaited()
