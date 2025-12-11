import asyncio
import contextlib
from asyncio import Task
from pathlib import Path

import openziti
from aiocache import Cache
from openziti.context import ZitiContext
from openziti.zitisock import ZitiSocket


class ZitiSocketCache:
    def __init__(
        self,
        identity_file: str | Path,
        ziti_ctx_timeout_ms: int = 10_000,
        ttl_seconds: float = 60.0,
        cleanup_interval: float = 10.0,
    ) -> None:
        self._identity_file = identity_file
        self._ziti_ctx_timeout_ms = ziti_ctx_timeout_ms
        self._ttl_seconds = ttl_seconds
        self._cleanup_interval = cleanup_interval

        self._ziti_ctx: ZitiContext | None = None
        self._cache = Cache(Cache.MEMORY)
        self._active_sockets: dict[str, ZitiSocket] = {}
        self._cleanup_task: Task | None = None

    def _get_ziti_ctx(self) -> ZitiContext:
        if self._ziti_ctx is None:
            ctx, err = openziti.load(str(self._identity_file), timeout=self._ziti_ctx_timeout_ms)
            if err != 0:
                raise Exception(f"Cannot create a Ziti context from the identity file: {err}")
            self._ziti_ctx = ctx
        return self._ziti_ctx

    async def _create_socket(self, key: str):
        return self._get_ziti_ctx().connect(key)

    async def get_or_create(self, key: str):
        sock = await self._cache.get(key)

        if sock:
            await self._cache.set(key, sock, ttl_seconds=self._ttl_seconds)
            self._active_sockets[key] = sock
            return sock

        sock = await self._create_socket(key)
        await self._cache.set(key, sock, ttl_seconds=self._ttl_seconds)
        self._active_sockets[key] = sock
        return sock

    async def invalidate(self, key: str):
        sock = await self._cache.get(key)
        if sock:
            await self._close_socket(sock)

        await self._cache.delete(key)
        self._active_sockets.pop(key, None)

    async def start(self):
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        # Warmup ziti context
        self._get_ziti_ctx()

    async def stop(self):
        """
        Cleanup: stop background task + close all sockets.
        """
        self._cleanup_task.cancel()
        with contextlib.suppress(Exception):
            await self._cleanup_task

        for sock in list(self._active_sockets.values()):
            await self._close_socket(sock)

        self._active_sockets.clear()
        await self._cache.clear()

    @staticmethod
    async def _close_socket(sock: ZitiSocket):
        with contextlib.suppress(Exception):
            sock.close()

    async def _periodic_cleanup(self):
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_once()
        except asyncio.CancelledError:
            return

    async def _cleanup_once(self):
        keys_now = set(await self._cache.keys())
        known_keys = set(self._active_sockets.keys())

        expired = known_keys - keys_now

        for key in expired:
            sock = self._active_sockets.pop(key, None)
            if sock:
                await self._close_socket(sock)
