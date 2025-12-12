import asyncio
import contextlib
import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any

from cachetools import TTLCache

from mrok.http.types import StreamPair

PoolItem = tuple[asyncio.StreamReader, asyncio.StreamWriter, float]

logger = logging.getLogger("mrok.proxy")


class ConnectionPool:
    def __init__(
        self,
        pool_name: str,
        factory: Callable[[], Awaitable[StreamPair]],
        *,
        initial_connections: int = 0,
        max_size: int = 10,
        idle_timeout: float = 30.0,
        reaper_interval: float = 5.0,
    ) -> None:
        if initial_connections < 0:
            raise ValueError("initial_connections must be >= 0")
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if initial_connections > max_size:
            raise ValueError("initial_connections cannot exceed max_size")
        self.pool_name = pool_name
        self.factory = factory
        self.initial_connections = initial_connections
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self.reaper_interval = reaper_interval

        self._pool: list[PoolItem] = []
        self._in_use = 0
        self._lock = asyncio.Lock()
        self._cond = asyncio.Condition()
        self._stop_event = asyncio.Event()

        self._started = False
        self._reaper_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._started:
            return
        self._reaper_task = asyncio.create_task(self._reaper())
        await self._prewarm()
        self._started = True

    async def stop(self) -> None:
        self._stop_event.set()
        if self._reaper_task is not None:
            self._reaper_task.cancel()
            with contextlib.suppress(Exception):
                await self._reaper_task

        to_close: list[asyncio.StreamWriter] = []
        async with self._lock:
            to_close = [writer for _, writer, _ in self._pool]
            self._pool.clear()
        for w in to_close:
            with contextlib.suppress(Exception):
                w.close()
                await w.wait_closed()

        async with self._cond:
            self._cond.notify_all()

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[StreamPair]:
        if not self._started:
            await self.start()
        reader, writer = await self._acquire()
        logger.info(
            f"Acquire stats for pool {self.pool_name}: "
            f"in_use={self._in_use}, size={len(self._pool)}"
        )
        try:
            yield (reader, writer)
        finally:
            await self._release(reader, writer)

    async def _prewarm(self) -> None:
        conns: list[PoolItem] = []
        needed = max(0, self.initial_connections - (self._in_use + len(self._pool)))
        for _ in range(needed):
            reader, writer = await self.factory()
            conns.append((reader, writer, time.time()))
        if conns:
            async with self._lock:
                self._pool.extend(conns)
            # notify any waiters
            async with self._cond:
                self._cond.notify_all()

    async def _acquire(self) -> StreamPair:  # type: ignore
        to_close: list[asyncio.StreamWriter] = []
        create_new = False
        while True:
            need_prewarm = False
            async with self._cond:
                now = time.time()
                if not self._pool:
                    need_prewarm = True
                while self._pool:
                    reader, writer, ts = self._pool.pop()
                    if now - ts <= self.idle_timeout and not writer.is_closing():
                        self._in_use += 1
                        return reader, writer
                    to_close.append(writer)

                total = self._in_use + len(self._pool)
                if total < self.max_size:
                    self._in_use += 1
                    create_new = True
                    break
                await self._cond.wait()

            if need_prewarm:
                await self._prewarm()
                continue

        for w in to_close:
            with contextlib.suppress(Exception):
                w.close()
                await w.wait_closed()

        if create_new:
            try:
                reader, writer = await self.factory()
            except Exception:
                async with self._cond:
                    if self._in_use > 0:
                        self._in_use -= 1
                    self._cond.notify()
                raise
            return reader, writer

    async def _release(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        async with self._cond:
            if self._in_use > 0:
                self._in_use -= 1

            if not writer.is_closing():
                self._pool.append((reader, writer, time.time()))

            self._cond.notify()
        logger.info(
            f"Release stats for pool {self.pool_name}: "
            f"in_use={self._in_use}, size={len(self._pool)}"
        )

    async def _reaper(self) -> None:
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self.reaper_interval)
                to_close: list[asyncio.StreamWriter] = []
                now = time.time()
                async with self._lock:
                    new_pool: list[PoolItem] = []
                    for reader, writer, ts in self._pool:
                        if now - ts > self.idle_timeout or writer.is_closing():
                            to_close.append(writer)
                        else:
                            new_pool.append((reader, writer, ts))
                    self._pool = new_pool

                for w in to_close:
                    with contextlib.suppress(Exception):
                        w.close()
                        await w.wait_closed()

                async with self._cond:
                    self._cond.notify_all()
        except asyncio.CancelledError:
            pass


class SlidingTTLCache(TTLCache):
    def __init__(
        self,
        *,
        maxsize: float,
        ttl: float,
        on_evict: Callable[[Any], Coroutine[Any, Any, None]] | None,
    ) -> None:
        super().__init__(maxsize=maxsize, ttl=ttl)
        self.on_evict = on_evict

    def __getitem__(self, key: Any) -> Any:
        value = super().__getitem__(key)
        super().__setitem__(key, value)
        return value

    def popitem(self) -> Any:
        key, value = super().popitem()
        if self.on_evict:
            asyncio.create_task(self.on_evict(value))
        return key, value


class PoolManager:
    def __init__(
        self,
        pool_factory: Callable[[Any], Awaitable[ConnectionPool]],
        idle_timeout: int = 300,
    ):
        self.factory = pool_factory
        self.cache = SlidingTTLCache(
            maxsize=float("inf"),
            ttl=idle_timeout,
            on_evict=self._close_pool,
        )

    async def _close_pool(self, pool: ConnectionPool):
        with contextlib.suppress(Exception):
            await pool.stop()

    async def get_pool(self, key) -> ConnectionPool:
        try:
            return self.cache[key]
        except KeyError:
            pool = await self.factory(key)
            await pool.start()
            self.cache[key] = pool
            return pool

    async def shutdown(self) -> None:
        pools = list(self.cache.values())
        for pool in pools:
            await self._close_pool(pool)
