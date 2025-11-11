import asyncio
import datetime
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mrok.agent.sidecar.store import RequestStore
from mrok.http.forwarder import ForwardAppBase

logger = logging.getLogger("mrok.proxy")

Scope = dict[str, Any]
ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


class ForwardApp(ForwardAppBase):
    def __init__(
        self,
        target_address: str | Path | tuple[str, int],
        read_chunk_size: int = 65536,
        store: RequestStore | None = None,
    ) -> None:
        super().__init__(read_chunk_size=read_chunk_size)
        self._target_address = target_address
        self._store = store
        self.capture_body = True

    async def select_backend(
        self,
        scope: Scope,
        headers: dict[str, str],
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter] | tuple[None, None]:
        if isinstance(self._target_address, tuple):
            return await asyncio.open_connection(*self._target_address)
        return await asyncio.open_unix_connection(str(self._target_address))

    async def on_response_complete(
        self,
        scope: Scope,
        status: int,
        headers: list[tuple[bytes, bytes]],
        headers_out: list[tuple[bytes, bytes]],
        start_time: float,
        request_buffer: bytearray,
        response_buffer: bytearray,
    ) -> None:
        if self._store is None:
            return

        request_data = {
            "method": scope["method"],
            "path": scope["path"],
            "raw_path": scope["raw_path"],
            "query_string": scope["query_string"],
            "request_body": request_buffer,
            "request_headers": headers,
            "response_body": response_buffer,
            "response_headers": headers_out,
            "status": status,
            "start": datetime.datetime.fromtimestamp(start_time),
            "duration": time.time() - start_time,
        }
        self._store.add(request_data)
