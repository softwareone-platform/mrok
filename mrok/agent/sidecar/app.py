import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from mrok.http.forwarder import ForwardAppBase
from mrok.http.pool import ConnectionPool
from mrok.http.types import Scope, StreamPair

logger = logging.getLogger("mrok.agent")


class ForwardApp(ForwardAppBase):
    def __init__(
        self,
        target_address: str | Path | tuple[str, int],
        read_chunk_size: int = 65536,
    ) -> None:
        super().__init__(
            read_chunk_size=read_chunk_size,
        )
        self._target_address = target_address
        self._pool = ConnectionPool(
            pool_name=str(self._target_address),
            factory=self.connect,
            initial_connections=5,
            max_size=100,
            idle_timeout=20.0,
            reaper_interval=5.0,
        )

    async def connect(self) -> StreamPair:
        if isinstance(self._target_address, tuple):
            return await asyncio.open_connection(*self._target_address)
        return await asyncio.open_unix_connection(str(self._target_address))

    async def startup(self):
        await self._pool.start()

    async def shutdown(self):
        await self._pool.stop()

    @asynccontextmanager
    async def select_backend(
        self,
        scope: Scope,
        headers: dict[str, str],
    ) -> AsyncGenerator[StreamPair, None]:
        async with self._pool.acquire() as (reader, writer):
            yield reader, writer
