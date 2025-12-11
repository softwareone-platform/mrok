import asyncio
import contextlib
import logging
from pathlib import Path

import openziti
from aiocache import Cache

from mrok.proxy.streams import CachedStreamReader, CachedStreamWriter
from mrok.proxy.types import StreamPair

logger = logging.getLogger("mrok.proxy")


class ZitiConnectionManager:
    def __init__(
        self,
        identity_file: str | Path,
        ziti_timeout_ms: int = 10000,
        ttl_seconds: float = 60.0,
        cleanup_interval: float = 10.0,
    ):
        self.identity_file = identity_file
        self.ziti_timeout_ms = ziti_timeout_ms
        self.ttl_seconds = ttl_seconds
        self.cleanup_interval = cleanup_interval

        self.cache = Cache(Cache.MEMORY)

        self._active_pairs: dict[str, StreamPair] = {}

        self._cleanup_task: asyncio.Task | None = None
        self._ziti_ctx: openziti.context.ZitiContext | None = None

    async def create_stream_pair(self, key: str) -> StreamPair:
        if not self._ziti_ctx:
            raise Exception("ZitiConnectionManager is not started")
        sock = self._ziti_ctx.connect(key)
        orig_reader, orig_writer = await asyncio.open_connection(sock=sock)

        reader = CachedStreamReader(orig_reader, key, self)
        writer = CachedStreamWriter(orig_writer, key, self)
        return (reader, writer)

    async def get_or_create(self, key: str) -> StreamPair:
        pair = await self.cache.get(key)

        if pair:
            logger.info(f"return cached connection for {key}")
            await self.cache.set(key, pair, ttl=self.ttl_seconds)
            self._active_pairs[key] = pair
            return pair

        pair = await self.create_stream_pair(key)
        await self.cache.set(key, pair, ttl=self.ttl_seconds)
        self._active_pairs[key] = pair
        logger.info(f"return new connection for {key}")
        return pair

    async def invalidate(self, key: str) -> None:
        logger.info(f"invalidating connection for {key}")
        pair = await self.cache.get(key)
        if pair:
            await self._close_pair(pair)

        await self.cache.delete(key)
        self._active_pairs.pop(key, None)

    async def start(self) -> None:
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        if self._ziti_ctx is None:
            ctx, err = openziti.load(str(self.identity_file), timeout=self.ziti_timeout_ms)
            if err != 0:
                raise Exception(f"Cannot create a Ziti context from the identity file: {err}")
            self._ziti_ctx = ctx

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(Exception):
                await self._cleanup_task

            for pair in list(self._active_pairs.values()):
                await self._close_pair(pair)

            self._active_pairs.clear()
            await self.cache.clear()
        openziti.shutdown()

    @staticmethod
    async def _close_pair(pair: StreamPair) -> None:
        reader, writer = pair
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()

    async def _periodic_cleanup(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_once()
        except asyncio.CancelledError:
            return

    async def _cleanup_once(self) -> None:
        # Keys currently stored in aiocache
        keys_in_cache = set(await self.cache.keys())
        # Keys we think are alive
        known_keys = set(self._active_pairs.keys())

        expired_keys = known_keys - keys_in_cache

        for key in expired_keys:
            pair = self._active_pairs.pop(key, None)
            if pair:
                await self._close_pair(pair)
