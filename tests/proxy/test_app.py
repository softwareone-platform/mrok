import asyncio
from collections.abc import Callable
from http import HTTPStatus
from typing import Any

import pytest
from httpcore import Request
from pytest_mock import MockerFixture

from mrok.proxy.app import HOP_BY_HOP_HEADERS, ProxyAppBase
from mrok.proxy.exceptions import ProxyError
from mrok.types.proxy import ASGIReceive, ASGISend, Message
from tests.types import ReceiveFactory, SendFactory


class _DummyResponse:
    def __init__(self, *, headers=None, status: int = 200, chunks: list[bytes] | None = None):
        self.headers = headers or [(b"content-type", b"text/plain")]
        self.status = status
        self._chunks = chunks or [b"ok"]

    @property
    def stream(self):
        async def _gen():
            await asyncio.sleep(0)
            for c in self._chunks:
                yield c

        return _gen()

    async def aclose(self) -> None:
        return None


def _find_header(hdrs, name: bytes):
    for k, v in hdrs:
        if k.lower() == name:
            return v
    return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "incoming_xf",
    [
        [],
        [
            (b"x-forwarded-for", b"1.2.3.4"),
            (b"x-forwarded-host", b"orig-host"),
            (b"x-forwarded-port", b"123"),
            (b"x-forwarded-proto", b"http"),
        ],
    ],
)
@pytest.mark.parametrize(
    "hop_by_hop_headers",
    [
        [],
        HOP_BY_HOP_HEADERS,
    ],
)
async def test_app_success(
    incoming_xf: list[tuple[bytes, bytes]],
    hop_by_hop_headers: list[bytes],
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
) -> None:
    sent: list[Message] = []

    captured: dict[str, Any] = {}
    resp_headers = [(b"content-type", b"text/plain")]
    resp_headers.extend([(hhh_name, b"value") for hhh_name in hop_by_hop_headers])

    class Pool:
        async def handle_async_request(self, req):
            captured["req"] = req
            return _DummyResponse(
                headers=resp_headers,
                status=200,
                chunks=[b"one", b"two"],
            )

    pool = Pool()

    class ProxyApp(ProxyAppBase):
        def setup_connection_pool(
            self,
            max_connections=1000,
            max_keepalive_connections=10,
            keepalive_expiry=120,
            retries=0,
        ):
            return pool

        def get_upstream_base_url(self, scope):
            return "http://upstream"

    app = ProxyApp()

    scope_headers: list[tuple[bytes, bytes]] = []
    scope_headers.extend(incoming_xf)
    scope_headers.extend([(hhh_name, b"value") for hhh_name in hop_by_hop_headers])

    scope = {
        "type": "http",
        "method": "POST",
        "raw_path": b"/foo",
        "query_string": b"param=value",
        "headers": scope_headers,
        "scheme": "https",
        "client": ("127.0.0.1", 12345),
        "server": ("localhost", 8000),
    }

    receive = receive_factory()
    send = send_factory(sent)

    await app(scope, receive, send)

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 200

    returned_headers = sent[0]["headers"]
    for k, _ in returned_headers:
        assert k.lower() not in HOP_BY_HOP_HEADERS

    # body chunks
    assert sent[1]["body"] == b"one"
    assert sent[1]["more_body"] is True
    assert sent[2]["body"] == b"two"
    assert sent[2]["more_body"] is True
    # final empty message
    assert sent[3]["body"] == b""
    assert sent[3]["more_body"] is False

    req: Request = captured["req"]

    assert bytes(req.url) == b"http://upstream/foo"
    for header in req.headers:
        assert header[0] not in HOP_BY_HOP_HEADERS

    client_ip = b"127.0.0.1"
    xf_for = _find_header(req.headers, b"x-forwarded-for")
    if incoming_xf:
        assert xf_for == b"1.2.3.4, " + client_ip
        assert _find_header(req.headers, b"x-forwarded-host") == b"orig-host"
        assert _find_header(req.headers, b"x-forwarded-port") == b"123"
    else:
        assert xf_for == client_ip
        assert _find_header(req.headers, b"x-forwarded-host") == b"localhost"
        assert _find_header(req.headers, b"x-forwarded-port") == b"8000"

    assert _find_header(req.headers, b"x-forwarded-proto") == b"https"


@pytest.mark.asyncio
async def test_proxyerror_returns_custom_status_and_message(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
) -> None:
    sent: list[Message] = []

    class App(ProxyAppBase):
        def setup_connection_pool(self, *a, **k):
            return None

        def get_upstream_base_url(self, scope):
            raise ProxyError(HTTPStatus.IM_A_TEAPOT, "short and stout")

    app = App()
    scope = {"type": "http", "path": "/"}
    receive = receive_factory()
    send = send_factory(sent)

    await app(scope, receive, send)

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == HTTPStatus.IM_A_TEAPOT
    assert sent[1]["body"] == b"short and stout"


@pytest.mark.asyncio
async def test_generic_exception_produces_502(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
) -> None:
    sent: list[Message] = []

    class Pool:
        async def handle_async_request(self, req):
            raise RuntimeError("boom")

    class ProxyApp(ProxyAppBase):
        def setup_connection_pool(self, *a, **k):
            return Pool()

        def get_upstream_base_url(self, scope):
            return "http://upstream"

    app = ProxyApp()
    scope = {"type": "http", "path": "/", "method": "GET"}
    receive = receive_factory()
    send = send_factory(sent)

    await app(scope, receive, send)

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 502
    assert sent[1]["body"] == b"Bad Gateway"


@pytest.mark.asyncio
async def test_lifespan_scope_no_send(
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
) -> None:
    class ProxyApp(ProxyAppBase):
        def setup_connection_pool(
            self,
            max_connections=1000,
            max_keepalive_connections=10,
            keepalive_expiry=120,
            retries=0,
        ):
            pass

        def get_upstream_base_url(self, scope):
            pass

    sends: list[Message] = []
    app = ProxyApp()
    scope = {"type": "lifespan"}
    receive = receive_factory()
    send = send_factory(sends)

    await app(scope, receive, send)
    assert sends == []


@pytest.mark.asyncio
async def test_non_http_scope_sends_unsupported(
    receive_factory: Callable[[], ASGIReceive],
    send_factory: Callable[[list[dict]], ASGISend],
) -> None:
    class ProxyApp(ProxyAppBase):
        def setup_connection_pool(
            self,
            max_connections=1000,
            max_keepalive_connections=10,
            keepalive_expiry=120,
            retries=0,
        ):
            pass

        def get_upstream_base_url(self, scope):
            pass

    sends: list[dict] = []
    app = ProxyApp()
    scope = {"type": "websocket"}
    receive = receive_factory()
    send = send_factory(sends)

    await app(scope, receive, send)

    assert len(sends) == 2
    assert sends[0]["type"] == "http.response.start"
    assert sends[0]["status"] == 500
    assert sends[1]["type"] == "http.response.body"
    assert sends[1]["body"] == b"Unsupported"
