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

    async def select_backend(
        self,
        scope: Scope,
        headers: dict[str, str],
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter] | tuple[None, None]:
        if isinstance(self._target_address, tuple):
            return await asyncio.open_connection(*self._target_address)
        return await asyncio.open_unix_connection(str(self._target_address))

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend) -> None:
        if self._store is None:
            await super().__call__(scope, receive, send)
            return

        start_time = time.time()
        request_data = {}

        async def capture_receive():
            event = await receive()
            if event["type"] == "http.request":
                request_data["request_body"] = event.get("body", b"")
            return event

        async def capture_send(event):
            if event["type"] == "http.response.body":
                request_data["response_body"] = event.get("body", b"")
            elif event["type"] == "http.response.start":
                request_data["status"] = event["status"]
            await send(event)

        try:
            await super().__call__(scope, capture_receive, capture_send)
        finally:
            request_data.update(
                {
                    "start": datetime.datetime.fromtimestamp(start_time),
                    "headers": scope["headers"],
                    "method": scope["method"],
                    "path": scope["path"],
                    "raw_path": scope["raw_path"],
                    "query_string": scope["query_string"],
                    "duration": time.time() - start_time,
                }
            )
            self._store.add(request_data)
