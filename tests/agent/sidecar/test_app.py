import asyncio
from typing import Any

import pytest
from pytest_mock import MockerFixture

from mrok.agent.sidecar.app import ForwardApp
from mrok.http.types import ASGIReceive, ASGISend


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
        # keep async signature; no awaits required
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


@pytest.mark.asyncio
async def test_select_backend_paths(mocker: MockerFixture):
    # Patch asyncio open_connection and open_unix_connection to return FakeReader/Writer
    async def fake_open_connection(host, port):
        await asyncio.sleep(0)
        return FakeReader([b"HTTP/1.1 200 OK\r\n\r\n", b"ok"]), FakeWriter()

    async def fake_open_unix_connection(path):
        await asyncio.sleep(0)
        return FakeReader([b"HTTP/1.1 200 OK\r\n\r\n", b"ok"]), FakeWriter()

    mocker.patch("asyncio.open_connection", new=fake_open_connection)
    mocker.patch("asyncio.open_unix_connection", new=fake_open_unix_connection)

    app_tcp = ForwardApp(("127.0.0.1", 9000))
    r1, w1 = await app_tcp.select_backend({}, {})
    assert isinstance(r1, FakeReader)

    app_unix = ForwardApp("/tmp/sock")
    r2, w2 = await app_unix.select_backend({}, {})
    assert isinstance(r2, FakeReader)
