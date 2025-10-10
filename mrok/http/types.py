from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any, Protocol

from mrok.datastructures import HTTPRequest, HTTPResponse

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

ASGIReceive = Callable[[], Awaitable[Message]]
ASGISend = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, ASGIReceive, ASGISend], Awaitable[None]]
RequestCompleteCallback = Callable[[HTTPRequest], Awaitable | None]
ResponseCompleteCallback = Callable[[HTTPResponse], Awaitable | None]


class StreamReaderWrapper(Protocol):
    async def read(self, n: int = -1) -> bytes: ...
    async def readexactly(self, n: int) -> bytes: ...
    async def readline(self) -> bytes: ...
    def at_eof(self) -> bool: ...

    @property
    def underlying(self) -> asyncio.StreamReader: ...


class StreamWriterWrapper(Protocol):
    def write(self, data: bytes) -> None: ...
    async def drain(self) -> None: ...
    def close(self) -> None: ...
    async def wait_closed(self) -> None: ...

    @property
    def transport(self): ...

    @property
    def underlying(self) -> asyncio.StreamWriter: ...


StreamReader = StreamReaderWrapper | asyncio.StreamReader
StreamWriter = StreamWriterWrapper | asyncio.StreamWriter
