from __future__ import annotations

from typing import Protocol

from mrok.http.types import StreamReader, StreamWriter

ConnectionKey = tuple[str, str | None]
CachedStream = tuple[StreamReader, StreamWriter]


class ConnectionCache(Protocol):
    async def invalidate(self, key: ConnectionKey) -> None: ...
