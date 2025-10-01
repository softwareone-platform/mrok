import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mrok.http.forwarder import ForwardAppBase

logger = logging.getLogger("mrok.proxy")

Scope = dict[str, Any]
ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


class ForwardApp(ForwardAppBase):
    def __init__(
        self, target_address: str | Path | tuple[str, int], read_chunk_size: int = 65536
    ) -> None:
        super().__init__(read_chunk_size=read_chunk_size)
        self._target_address = target_address

    async def select_backend(
        self,
        scope: Scope,
        headers: dict[str, str],
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter] | tuple[None, None]:
        if isinstance(self._target_address, tuple):
            return await asyncio.open_connection(*self._target_address)
        return await asyncio.open_unix_connection(str(self._target_address))
