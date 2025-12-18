import asyncio

from httpcore import AsyncNetworkStream

from mrok.proxy.types import ASGIReceive


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
