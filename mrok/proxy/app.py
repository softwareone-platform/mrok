import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mrok.conf import get_settings
from mrok.http.forwarder import ForwardAppBase
from mrok.http.types import StreamReader, StreamWriter
from mrok.proxy.ziti import ZitiConnectionManager

logger = logging.getLogger("mrok.proxy")

Scope = dict[str, Any]
ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


class ProxyError(Exception):
    pass


class ProxyApp(ForwardAppBase):
    def __init__(
        self,
        identity_file: str | Path,
        *,
        read_chunk_size: int = 65536,
        ziti_connection_ttl_seconds: float = 60,
        ziti_conn_cache_purge_interval_seconds: float = 10,
    ) -> None:
        super().__init__(read_chunk_size=read_chunk_size)
        settings = get_settings()
        self._identity_file = identity_file
        self._proxy_wildcard_domain = (
            settings.proxy.domain
            if settings.proxy.domain[0] == "."
            else f".{settings.proxy.domain}"
        )
        self._conn_manager = ZitiConnectionManager(
            identity_file,
            ttl_seconds=ziti_connection_ttl_seconds,
            purge_interval=ziti_conn_cache_purge_interval_seconds,
        )

    def get_target_name(self, headers: dict[str, str]) -> str:
        header_value = headers.get("x-forwarded-for", headers.get("host"))
        if not header_value:
            raise ProxyError(
                "Cannot determine the target OpenZiti service/terminator name, "
                "neither Host nor X-Forwarded-For headers have been sent in the request.",
            )

        if not header_value.endswith(self._proxy_wildcard_domain):
            raise ProxyError(
                f"Unexpected value for Host or X-Forwarded-For header: `{header_value}`."
            )

        return header_value[: -len(self._proxy_wildcard_domain)]

    async def startup(self):
        await self._conn_manager.start()

    async def shutdown(self):
        await self._conn_manager.stop()

    async def select_backend(
        self,
        scope: Scope,
        headers: dict[str, str],
    ) -> tuple[StreamReader, StreamWriter] | tuple[None, None]:
        target_name = self.get_target_name(headers)

        return await self._conn_manager.get(target_name)
