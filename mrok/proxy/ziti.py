"""Ziti-backed connection manager for the proxy.

This manager owns creation of connections via an OpenZiti context, wraps
streams to observe IO errors, evicts idle entries, and serializes creation
per-key.
"""

import asyncio
import logging
import time
from pathlib import Path

# typing imports intentionally minimized
import openziti

from mrok.http.types import StreamReader, StreamWriter
from mrok.proxy.dataclasses import CachedStreamEntry
from mrok.proxy.streams import CachedStreamReader, CachedStreamWriter
from mrok.proxy.types import CachedStream, ConnectionKey

logger = logging.getLogger("mrok.proxy")


class ZitiConnectionManager:
    def __init__(
        self,
        identity_file: str | Path,
        ziti_timeout_ms: int = 10000,
        ttl_seconds: float = 60.0,
        purge_interval: float = 10.0,
    ):
        self._identity_file = identity_file
        self._ziti_ctx = None
        self._ziti_timeout_ms = ziti_timeout_ms
        self._ttl = float(ttl_seconds)
        self._purge_interval = float(purge_interval)
        self._cache: dict[ConnectionKey, CachedStreamEntry] = {}
        self._lock = asyncio.Lock()
        self._in_progress: dict[ConnectionKey, asyncio.Lock] = {}
        self._purge_task: asyncio.Task | None = None

    async def get(self, target: str) -> tuple[StreamReader, StreamWriter] | tuple[None, None]:
        head, _, tail = target.partition(".")
        terminator = target if head and tail else ""
        service = tail if tail else head
        r, w = await self._get_or_create_key((service, terminator))
        return r, w

    async def invalidate(self, key: ConnectionKey) -> None:
        async with self._lock:
            item = self._cache.pop(key, None)
        if item is None:
            return
        await self._close_writer(item.writer)

    async def start(self) -> None:
        if self._ziti_ctx is None:
            ctx, err = openziti.load(str(self._identity_file), timeout=self._ziti_timeout_ms)
            if err != 0:
                raise Exception(f"Cannot create a Ziti context from the identity file: {err}")
            self._ziti_ctx = ctx
        if self._purge_task is None:
            self._purge_task = asyncio.create_task(self._purge_loop())
            logger.info("Ziti connection manager started")

    async def stop(self) -> None:
        if self._purge_task is not None:
            self._purge_task.cancel()
            try:
                await self._purge_task
            except asyncio.CancelledError:
                logger.debug("Purge task was cancelled")
            except Exception as e:
                logger.warning(f"An error occurred stopping the purge task: {e}")
            self._purge_task = None
            logger.info("Ziti connection manager stopped")

        async with self._lock:
            items = list(self._cache.items())
            self._cache.clear()

        for _, item in items:
            await self._close_writer(item.writer)

    async def _purge_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._purge_interval)
                await self._purge_once()
        except asyncio.CancelledError:
            return

    async def _purge_once(self) -> None:
        to_close: list[tuple[StreamReader, StreamWriter]] = []
        async with self._lock:
            now = time.time()
            for key, item in list(self._cache.items()):
                if now - item.last_access > self._ttl:
                    to_close.append((item.reader, item.writer))
                    del self._cache[key]

        for _, writer in to_close:
            writer.close()
            await self._close_writer(writer)

    def _is_writer_closed(self, writer: StreamWriter) -> bool:
        return writer.transport.is_closing()

    async def _close_writer(self, writer: StreamWriter) -> None:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception as e:
            logger.debug(f"Error closing writer: {e}")

    async def _get_or_create_key(self, key: ConnectionKey) -> CachedStream:
        """Internal: create or return a cached wrapped pair for the concrete key."""
        await self._purge_once()
        to_close = None
        async with self._lock:
            if key in self._cache:
                now = time.time()
                item = self._cache[key]
                reader, writer = item.reader, item.writer
                if not self._is_writer_closed(writer) and not reader.at_eof():
                    self._cache[key] = CachedStreamEntry(reader, writer, now)
                    return reader, writer
                to_close = writer
                del self._cache[key]

            lock = self._in_progress.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._in_progress[key] = lock

        if to_close:
            await self._close_writer(to_close)

        async with lock:
            try:
                # # double-check cache after acquiring the per-key lock
                # async with self._lock:
                #     now = time.time()
                #     if key in self._cache:
                #         r, w, _ = self._cache[key]
                #         if not self._is_writer_closed(w) and not r.at_eof():
                #             self._cache[key] = (r, w, now)
                #             return r, w

                # perform creation via ziti context
                extension, instance = key
                logger.info(f"Create connection to {extension}: {instance}")
                # loop = asyncio.get_running_loop()
                # sock = await loop.run_in_executor(None, self._ziti_ctx.connect,
                # extension, instance)
                if instance:
                    sock = self._ziti_ctx.connect(
                        extension, terminator=instance
                    )  # , terminator=instance)
                else:
                    sock = self._ziti_ctx.connect(extension)
                orig_reader, orig_writer = await asyncio.open_connection(sock=sock)

                reader = CachedStreamReader(orig_reader, key, self)
                writer = CachedStreamWriter(orig_writer, key, self)

                async with self._lock:
                    self._cache[key] = CachedStreamEntry(reader, writer, time.time())

                return reader, writer
            finally:
                async with self._lock:
                    self._in_progress.pop(key, None)
