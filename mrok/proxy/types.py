from __future__ import annotations

from typing import Protocol

from mrok.http.types import StreamReader, StreamWriter

StreamPair = tuple[StreamReader, StreamWriter]


class ConnectionCache(Protocol):
    async def invalidate(self, key: str) -> None: ...
