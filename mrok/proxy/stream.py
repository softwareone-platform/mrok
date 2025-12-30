import asyncio
import select
import sys
from typing import Any

from httpcore import AsyncNetworkStream

from mrok.types.proxy import ASGIReceive


def is_readable(sock):  # pragma: no cover
    # Stolen from
    # https://github.com/python-trio/trio/blob/20ee2b1b7376db637435d80e266212a35837ddcc/trio/_socket.py#L471C1-L478C31

    # use select.select on Windows, and select.poll everywhere else
    if sys.platform == "win32":
        rready, _, _ = select.select([sock], [], [], 0)
        return bool(rready)
    p = select.poll()
    p.register(sock, select.POLLIN)
    return bool(p.poll(0))


class AIONetworkStream(AsyncNetworkStream):
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def read(self, n: int, timeout: float | None = None) -> bytes:
        return await asyncio.wait_for(self._reader.read(n), timeout)

    async def write(self, data: bytes, timeout: float | None = None) -> None:
        self._writer.write(data)
        await asyncio.wait_for(self._writer.drain(), timeout)

    async def aclose(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()

    def get_extra_info(self, info: str) -> Any:
        transport = self._writer.transport
        if info == "is_readable":
            sock = transport.get_extra_info("socket")
            return is_readable(sock)
        return transport.get_extra_info(info)


class ASGIRequestBodyStream:
    def __init__(self, receive: ASGIReceive):
        self._receive = receive
        self._more_body = True

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        if not self._more_body:
            raise StopAsyncIteration

        msg = await self._receive()
        if msg["type"] == "http.request":
            chunk = msg.get("body", b"")
            self._more_body = msg.get("more_body", False)
            return chunk
        elif msg["type"] == "http.disconnect":
            raise Exception("Client disconnected.")

        raise Exception("Unexpected asgi message.")
