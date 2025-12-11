import asyncio

from mrok.proxy.types import ConnectionCache


class CachedStreamReader:
    def __init__(
        self,
        reader: asyncio.StreamReader,
        key: str,
        manager: ConnectionCache,
    ):
        self._reader = reader
        self._key = key
        self._manager = manager

    async def read(self, n: int = -1) -> bytes:
        try:
            return await self._reader.read(n)
        except (
            asyncio.CancelledError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
            BrokenPipeError,
            ConnectionAbortedError,
            ConnectionResetError,
            RuntimeError,
            TimeoutError,
            UnicodeDecodeError,
        ):
            asyncio.create_task(self._manager.invalidate(self._key))
            raise

    async def readexactly(self, n: int) -> bytes:
        try:
            return await self._reader.readexactly(n)
        except (
            asyncio.CancelledError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
            BrokenPipeError,
            ConnectionAbortedError,
            ConnectionResetError,
            RuntimeError,
            TimeoutError,
            UnicodeDecodeError,
        ):
            asyncio.create_task(self._manager.invalidate(self._key))
            raise

    async def readline(self) -> bytes:
        try:
            return await self._reader.readline()
        except (
            asyncio.CancelledError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
            BrokenPipeError,
            ConnectionAbortedError,
            ConnectionResetError,
            RuntimeError,
            TimeoutError,
            UnicodeDecodeError,
        ):
            asyncio.create_task(self._manager.invalidate(self._key))
            raise

    def at_eof(self) -> bool:
        return self._reader.at_eof()

    @property
    def underlying(self) -> asyncio.StreamReader:
        return self._reader


class CachedStreamWriter:
    def __init__(
        self,
        writer: asyncio.StreamWriter,
        key: str,
        manager: ConnectionCache,
    ):
        self._writer = writer
        self._key = key
        self._manager = manager

    def write(self, data: bytes) -> None:
        try:
            return self._writer.write(data)
        except (RuntimeError, TypeError):
            asyncio.create_task(self._manager.invalidate(self._key))
            raise

    async def drain(self) -> None:
        try:
            return await self._writer.drain()
        except (
            asyncio.CancelledError,
            BrokenPipeError,
            ConnectionAbortedError,
            ConnectionResetError,
            RuntimeError,
            TimeoutError,
        ):
            asyncio.create_task(self._manager.invalidate(self._key))
            raise

    def close(self) -> None:
        return self._writer.close()

    async def wait_closed(self) -> None:
        try:
            return await self._writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError):
            asyncio.create_task(self._manager.invalidate(self._key))
            raise

    @property
    def transport(self):
        return self._writer.transport

    @property
    def underlying(self) -> asyncio.StreamWriter:
        return self._writer
