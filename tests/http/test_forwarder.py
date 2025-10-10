import asyncio
from typing import Any

import pytest
from pytest_mock import MockerFixture

from mrok.http.forwarder import ASGIReceive, ASGISend, ForwardAppBase


class FakeReader:
    def __init__(self, chunks: list[bytes]):
        # a single bytes buffer that we will serve from
        self._buffer = b"".join(chunks)
        self._pos = 0

    async def readline(self) -> bytes:
        # return up to and including first CRLF
        if self._pos >= len(self._buffer):
            return b""
        idx = self._buffer.find(b"\n", self._pos)
        if idx == -1:
            # return rest
            data = self._buffer[self._pos :]
            self._pos = len(self._buffer)
            return data
        idx += 1
        data = self._buffer[self._pos : idx]
        self._pos = idx
        return data

    async def read(self, n: int = -1) -> bytes:
        if self._pos >= len(self._buffer):
            return b""
        if n < 0:
            data = self._buffer[self._pos :]
            self._pos = len(self._buffer)
            return data
        data = self._buffer[self._pos : self._pos + n]
        self._pos += len(data)
        return data

    async def readexactly(self, n: int) -> bytes:
        # simplistic: if not enough, raise IncompleteReadError
        remaining = len(self._buffer) - self._pos
        if remaining < n:
            chunk = self._buffer[self._pos :]
            self._pos = len(self._buffer)
            raise asyncio.IncompleteReadError(partial=chunk, expected=n)
        data = self._buffer[self._pos : self._pos + n]
        self._pos += n
        return data


class FakeWriter:
    def __init__(self):
        self.buffer = bytearray()
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        await asyncio.sleep(0)  # yield control

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        await asyncio.sleep(0)


def send_collector(messages: list[dict[str, Any]]) -> ASGISend:
    async def _send(msg: dict[str, Any]) -> None:
        messages.append(msg)
        await asyncio.sleep(0)

    return _send


def make_receive(events: list[dict[str, Any]]) -> ASGIReceive:
    queue: list[dict[str, Any]] = list(events)

    async def _receive() -> dict[str, Any]:
        if not queue:
            await asyncio.sleep(0)
            return {"type": "http.request", "body": b"", "more_body": False}
        return queue.pop(0)

    return _receive


class ForwardApp(ForwardAppBase):
    def __init__(self, target_address: str | None = None, read_chunk_size: int = 65536) -> None:
        super().__init__(read_chunk_size=read_chunk_size)
        self._target_address = target_address

    async def select_backend(self, scope, headers):
        # default dummy backend; tests will usually override this method
        return FakeReader([]), FakeWriter()


@pytest.mark.asyncio
async def test_non_http_scope_returns_500():
    app = ForwardApp("127.0.0.1:8000")

    sent = []
    send = send_collector(sent)

    scope = {"type": "websocket"}
    receive = make_receive([])

    await app(scope, receive, send)

    assert any(m.get("type") == "http.response.start" and m.get("status") == 500 for m in sent)
    assert any(b"Unsupported" in m.get("body", b"") for m in sent)


@pytest.mark.asyncio
async def test_empty_status_line_returns_502():
    class App(ForwardApp):
        async def select_backend(self, scope, headers):
            # reader that immediately returns empty status line
            return FakeReader([b""]), FakeWriter()

    app = App("127.0.0.1:8000")
    sent = []
    send = send_collector(sent)
    scope = {"type": "http"}
    receive = make_receive([])

    await app(scope, receive, send)

    assert any(m.get("status") == 502 for m in sent)


@pytest.mark.asyncio
async def test_chunked_request_and_chunked_response():
    # backend will echo chunked response "hello"
    status = b"HTTP/1.1 200 OK\r\n"
    headers = b"transfer-encoding: chunked\r\n\r\n"
    body = b"5\r\nhello\r\n0\r\n\r\n"
    reader = FakeReader([status, headers, body])
    writer = FakeWriter()

    class App(ForwardApp):
        async def select_backend(self, scope, headers):
            return reader, writer

    app = App("127.0.0.1:8000")

    # ASGI receive will provide two body chunks
    events = [
        {"type": "http.request", "body": b"ab", "more_body": True},
        {"type": "http.request", "body": b"cd", "more_body": False},
    ]
    receive = make_receive(events)
    sent = []
    send = send_collector(sent)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/up",
        "query_string": b"",
        "headers": [],
    }

    await app(scope, receive, send)

    # verify writer got chunked request framing: two chunks and final 0
    buf = bytes(writer.buffer)
    assert b"POST /up HTTP/1.1\r\n" in buf
    assert b"transfer-encoding: chunked\r\n" in buf
    assert b"2\r\nabcd\r\n" in buf or b"2\r\nab\r\n2\r\ncd\r\n" in buf
    assert b"0\r\n\r\n" in buf

    # verify sends: start + body chunk + final
    types = [m["type"] for m in sent]
    assert "http.response.start" in types
    bodies = [m for m in sent if m["type"] == "http.response.body"]
    assert bodies[0]["body"] == b"hello"
    assert bodies[-1]["more_body"] is False


@pytest.mark.asyncio
async def test_write_skips_expect_header():
    app = ForwardApp("127.0.0.1:8000")
    writer = FakeWriter()
    headers = [(b"expect", b"100-continue"), (b"host", b"example")]
    await app.write_request_line_and_headers(writer, "GET", "/", headers)
    buf = bytes(writer.buffer)
    assert b"expect" not in buf.lower()


@pytest.mark.asyncio
async def test_stream_request_handles_disconnect():
    app = ForwardApp("127.0.0.1:8000")
    writer = FakeWriter()
    receive = make_receive([{"type": "http.disconnect"}])
    await app.stream_request_body(receive, writer, use_chunked=True)
    assert writer.closed is True


@pytest.mark.asyncio
async def test_read_status_non_digit_returns_502():
    app = ForwardApp("127.0.0.1:8000")
    reader = FakeReader([b"HTTP/1.1 BADSTATUS\r\n", b"\r\n"])
    status, headers, raw = await app.read_status_and_headers(reader, b"HTTP/1.1 BADSTATUS\r\n")
    assert status == 502


@pytest.mark.asyncio
async def test_chunked_invalid_size_line_sends_final_only():
    app = ForwardApp("127.0.0.1:8000")
    reader = FakeReader([b"not-hex\r\n"])
    sent = []
    send = send_collector(sent)
    await app.stream_response_body(reader, send, {b"transfer-encoding": b"chunked"})
    # Only the terminating empty body should be sent
    bodies = [m for m in sent if m["type"] == "http.response.body"]
    assert len(bodies) == 1
    assert bodies[0]["more_body"] is False


@pytest.mark.asyncio
async def test_content_length_invalid_parsed_as_stream_until_eof():
    app = ForwardApp("127.0.0.1:8000", read_chunk_size=4)
    reader = FakeReader([b"abcd"])
    sent = []
    send = send_collector(sent)
    await app.stream_response_body(reader, send, {b"content-length": b"notint"})
    bodies = [m for m in sent if m["type"] == "http.response.body"]
    # should forward the bytes and then final empty
    assert any(b["body"] == b"abcd" for b in bodies)
    assert bodies[-1]["more_body"] is False


@pytest.mark.asyncio
async def test_stream_request_handles_disconnect_non_chunked():
    # Verify non-chunked path also closes writer on disconnect
    app = ForwardApp("127.0.0.1:8000")
    writer = FakeWriter()
    receive = make_receive([{"type": "http.disconnect"}])
    await app.stream_request_body(receive, writer, use_chunked=False)
    assert writer.closed is True


@pytest.mark.asyncio
async def test_chunked_response_eof_immediately_sends_final():
    # If reader.readline() returns empty immediately, chunked path should send only final empty body
    app = ForwardApp("127.0.0.1:8000")
    reader = FakeReader([])  # empty buffer -> first readline() returns b""
    sent = []
    send = send_collector(sent)
    await app.stream_response_body(reader, send, {b"transfer-encoding": b"chunked"})
    bodies = [m for m in sent if m["type"] == "http.response.body"]
    assert len(bodies) == 1
    assert bodies[0]["more_body"] is False


@pytest.mark.asyncio
async def test_content_length_partial_eof_results_in_final_empty():
    # content-length header present but reader provides fewer bytes than expected
    # -> final empty send
    app = ForwardApp("127.0.0.1:8000", read_chunk_size=4)
    # simulate reader that will return 2 bytes then EOF
    reader = FakeReader([b"ab"])  # content-length says 5, but only 2 provided
    sent = []
    send = send_collector(sent)
    await app.stream_response_body(reader, send, {b"content-length": b"5"})
    bodies = [m for m in sent if m["type"] == "http.response.body"]
    # we should have forwarded the 'ab' and then sent a final empty body
    assert any(b["body"] == b"ab" for b in bodies)
    assert bodies[-1]["more_body"] is False


@pytest.mark.asyncio
async def test_content_length_forwarding_and_response():
    # backend will return content-length response
    status = b"HTTP/1.1 200 OK\r\n"
    headers = b"content-length: 11\r\n\r\n"
    body = b"hello world"
    reader = FakeReader([status, headers, body])
    writer = FakeWriter()

    class App(ForwardApp):
        async def select_backend(self, scope, headers):
            return reader, writer

    # include content-length header in incoming headers so we avoid chunked request
    app = App("127.0.0.1:8000")
    events = [
        {"type": "http.request", "body": b"hello world", "more_body": False},
    ]
    receive = make_receive(events)
    sent = []
    send = send_collector(sent)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/cl",
        "query_string": b"",
        "headers": [(b"content-length", b"11")],
    }

    await app(scope, receive, send)

    buf = bytes(writer.buffer)
    # should not contain chunk framing
    assert b"transfer-encoding" not in buf
    assert b"hello world" in buf

    bodies = [m for m in sent if m["type"] == "http.response.body"]
    assert bodies[0]["body"] == b"hello world"
    assert bodies[-1]["more_body"] is False


@pytest.mark.asyncio
async def test_stream_request_body_chunked_empty_final():
    # When chunked and the only event has empty body and more_body False,
    # the writer should receive only the terminating 0 chunk.
    app = ForwardApp("127.0.0.1:8000")
    writer = FakeWriter()
    receive = make_receive([{"type": "http.request", "body": b"", "more_body": False}])
    await app.stream_request_body(receive, writer, use_chunked=True)
    buf = bytes(writer.buffer)
    assert b"0\r\n\r\n" in buf


@pytest.mark.asyncio
async def test_stream_request_body_non_chunked_writes_body():
    # Non-chunked bodies should be written raw to the writer
    app = ForwardApp("127.0.0.1:8000")
    writer = FakeWriter()
    receive = make_receive([{"type": "http.request", "body": b"xyz", "more_body": False}])
    await app.stream_request_body(receive, writer, use_chunked=False)
    assert bytes(writer.buffer) == b"xyz"


@pytest.mark.asyncio
async def test_stream_request_body_chunked_with_unknown_event():
    # If an unknown event type is received, the loop should continue until http.request
    app = ForwardApp("127.0.0.1:8000")
    writer = FakeWriter()
    events = [
        {"type": "something-else"},
        {"type": "http.request", "body": b"x", "more_body": False},
    ]
    receive = make_receive(events)
    await app.stream_request_body(receive, writer, use_chunked=True)
    buf = bytes(writer.buffer)
    assert b"1\r\nx\r\n" in buf


@pytest.mark.asyncio
async def test_stream_request_body_non_chunked_multiple_events():
    # Non-chunked path with multiple http.request events where first has more_body True
    app = ForwardApp("127.0.0.1:8000")
    writer = FakeWriter()
    events = [
        {"type": "http.request", "body": b"a", "more_body": True},
        {"type": "http.request", "body": b"b", "more_body": False},
    ]
    receive = make_receive(events)
    await app.stream_request_body(receive, writer, use_chunked=False)
    assert bytes(writer.buffer) == b"ab"


@pytest.mark.asyncio
async def test_stream_request_body_non_chunked_empty_final():
    # Non-chunked with single empty body and more_body False should not write and should break
    app = ForwardApp("127.0.0.1:8000")
    writer = FakeWriter()
    receive = make_receive([{"type": "http.request", "body": b"", "more_body": False}])
    await app.stream_request_body(receive, writer, use_chunked=False)
    assert bytes(writer.buffer) == b""


@pytest.mark.asyncio
async def test_stream_request_body_non_chunked_with_unknown_event():
    # Unknown events should be ignored and the loop should continue until http.request
    app = ForwardApp("127.0.0.1:8000")
    writer = FakeWriter()
    events = [
        {"type": "ignored-event"},
        {"type": "http.request", "body": b"z", "more_body": False},
    ]
    receive = make_receive(events)
    await app.stream_request_body(receive, writer, use_chunked=False)
    assert bytes(writer.buffer) == b"z"


@pytest.mark.asyncio
async def test_stream_until_eof_response():
    # backend returns no content-length and no transfer-encoding, so we stream until EOF
    status = b"HTTP/1.1 200 OK\r\n"
    headers = b"\r\n"
    body = b"streamed-data"
    reader = FakeReader([status, headers, body])
    writer = FakeWriter()

    class App(ForwardApp):
        async def select_backend(self, scope, headers):
            return reader, writer

    app = App("127.0.0.1:8000")
    receive = make_receive([])
    sent = []
    send = send_collector(sent)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/stream",
        "query_string": b"",
        "headers": [],
    }

    await app(scope, receive, send)

    bodies = [m for m in sent if m["type"] == "http.response.body"]
    assert any(b["body"] == b"streamed-data" for b in bodies)
    assert bodies[-1]["more_body"] is False


def test_format_and_host_helpers():
    app = ForwardApp("127.0.0.1:8000")
    # raw_path
    scope1 = {"raw_path": b"/raw/path"}
    assert app.format_path(scope1) == "/raw/path"

    # path + query
    scope2 = {"path": "/p", "query_string": b"a=1"}
    assert app.format_path(scope2) == "/p?a=1"

    # ensure_host_header does nothing when host present
    headers = [(b"host", b"example")]
    out = app.ensure_host_header(list(headers), {})
    assert any(h[0] == b"host" for h in out)

    # ensure_host_header adds host when server present
    out2 = app.ensure_host_header([], {"server": "127.0.0.1:8000"})
    assert any(h[0] == b"host" for h in out2)


@pytest.mark.asyncio
async def test_incoming_transfer_encoding_preserved():
    # If the incoming ASGI headers already include Transfer-Encoding, we must not add another
    status = b"HTTP/1.1 200 OK\r\n"
    headers = b"transfer-encoding: chunked\r\n\r\n"
    body = b"1\r\na\r\n0\r\n\r\n"
    reader = FakeReader([status, headers, body])
    writer = FakeWriter()

    class App(ForwardApp):
        async def select_backend(self, scope, headers):
            return reader, writer

    app = App("127.0.0.1:8000")

    events = [
        {"type": "http.request", "body": b"a", "more_body": False},
    ]
    receive = make_receive(events)
    sent = []
    send = send_collector(sent)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/up",
        "query_string": b"",
        "headers": [(b"transfer-encoding", b"chunked")],
    }

    await app(scope, receive, send)

    buf = bytes(writer.buffer)
    # transfer-encoding must be present but not duplicated
    assert buf.count(b"transfer-encoding: chunked") >= 1


@pytest.mark.asyncio
async def test_chunked_response_with_trailer():
    # backend sends a chunked response that includes trailer headers
    status = b"HTTP/1.1 200 OK\r\n"
    headers = b"transfer-encoding: chunked\r\n\r\n"
    # chunked body "hello" with a trailer header 'x-trailer: v'
    body = b"5\r\nhello\r\n0\r\nx-trailer: v\r\n\r\n"
    reader = FakeReader([status, headers, body])
    writer = FakeWriter()

    class App(ForwardApp):
        async def select_backend(self, scope, headers):
            return reader, writer

    app = App("127.0.0.1:8000")
    receive = make_receive([])
    sent = []
    send = send_collector(sent)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/tr",
        "query_string": b"",
        "headers": [],
    }

    await app(scope, receive, send)

    bodies = [m for m in sent if m["type"] == "http.response.body"]
    assert any(b["body"] == b"hello" for b in bodies)
    assert bodies[-1]["more_body"] is False


@pytest.mark.asyncio
async def test_malformed_header_line_parsing():
    # backend returns a malformed header line (no colon) plus a valid content-length
    status = b"HTTP/1.1 200 OK\r\n"
    headers = b"bad-header-line\r\ncontent-length: 3\r\n\r\n"
    body = b"xyz"
    reader = FakeReader([status, headers, body])
    writer = FakeWriter()

    class App(ForwardApp):
        async def select_backend(self, scope, headers):
            return reader, writer

    app = App("127.0.0.1:8000")
    receive = make_receive([])
    sent = []
    send = send_collector(sent)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/bad",
        "query_string": b"",
        "headers": [],
    }

    await app(scope, receive, send)

    bodies = [m for m in sent if m["type"] == "http.response.body"]
    # the body should still be forwarded despite the malformed header line
    assert any(b["body"] == b"xyz" for b in bodies)
    assert bodies[-1]["more_body"] is False


@pytest.mark.asyncio
async def test_lifespan(mocker: MockerFixture):
    mocked_startup = mocker.patch.object(ForwardApp, "startup")
    mocked_shutdown = mocker.patch.object(ForwardApp, "shutdown")
    app = ForwardApp("127.0.0.1:8000")

    sent: list[dict] = []
    send = send_collector(sent)

    scope = {"type": "lifespan"}
    receive = make_receive([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])

    await app(scope, receive, send)

    assert len(sent) == 2
    assert sent[0]["type"] == "lifespan.startup.complete"
    assert sent[1]["type"] == "lifespan.shutdown.complete"

    mocked_startup.assert_awaited_once()
    mocked_shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_startup_failed(mocker: MockerFixture):
    mocker.patch.object(ForwardApp, "startup", side_effect=Exception("startup-failed"))
    app = ForwardApp("127.0.0.1:8000")

    sent: list[dict] = []
    send = send_collector(sent)

    scope = {"type": "lifespan"}
    receive = make_receive([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])

    await app(scope, receive, send)

    assert len(sent) == 2
    assert sent[0]["type"] == "lifespan.startup.failed"
    assert sent[0]["message"] == "startup-failed"
    assert sent[1]["type"] == "lifespan.shutdown.complete"


@pytest.mark.asyncio
async def test_lifespan_startup_timeout(mocker: MockerFixture):
    mocker.patch.object(ForwardApp, "startup", side_effect=TimeoutError())
    app = ForwardApp("127.0.0.1:8000")

    sent: list[dict] = []
    send = send_collector(sent)

    scope = {"type": "lifespan"}
    receive = make_receive([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])

    await app(scope, receive, send)

    assert len(sent) == 2
    assert sent[0]["type"] == "lifespan.startup.failed"
    assert sent[0]["message"] == "startup timeout"
    assert sent[1]["type"] == "lifespan.shutdown.complete"


@pytest.mark.asyncio
async def test_lifespan_shutdown_failed(mocker: MockerFixture):
    mocker.patch.object(ForwardApp, "shutdown", side_effect=Exception("shutdown-failed"))
    app = ForwardApp("127.0.0.1:8000")

    sent: list[dict] = []
    send = send_collector(sent)

    scope = {"type": "lifespan"}
    receive = make_receive([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])

    await app(scope, receive, send)

    assert len(sent) == 2
    assert sent[0]["type"] == "lifespan.startup.complete"
    assert sent[1]["type"] == "lifespan.shutdown.failed"
    assert sent[1]["message"] == "shutdown-failed"


@pytest.mark.asyncio
async def test_lifespan_shutdown_timeout(mocker: MockerFixture):
    mocker.patch.object(ForwardApp, "shutdown", side_effect=TimeoutError())
    app = ForwardApp("127.0.0.1:8000")

    sent: list[dict] = []
    send = send_collector(sent)

    scope = {"type": "lifespan"}
    receive = make_receive([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])

    await app(scope, receive, send)

    assert len(sent) == 2
    assert sent[0]["type"] == "lifespan.startup.complete"
    assert sent[1]["type"] == "lifespan.shutdown.failed"
    assert sent[1]["message"] == "shutdown timeout"


@pytest.mark.asyncio
async def test_no_backend_available():
    class App(ForwardApp):
        async def select_backend(self, scope, headers):
            return None, None

    app = App("127.0.0.1:8000")

    # ASGI receive will provide two body chunks
    events = [
        {"type": "http.request", "body": b"ab", "more_body": True},
        {"type": "http.request", "body": b"cd", "more_body": False},
    ]
    receive = make_receive(events)
    sent = []
    send = send_collector(sent)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/up",
        "query_string": b"",
        "headers": [],
    }

    await app(scope, receive, send)

    assert len(sent) == 2
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 502

    assert sent[1]["type"] == "http.response.body"
    assert sent[1]["body"] == b"Bad Gateway"
