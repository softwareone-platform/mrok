import asyncio
import logging
from pathlib import Path

from mrok.conf import get_settings
from mrok.http.forwarder import ForwardAppBase
from mrok.http.types import Scope, StreamReader, StreamWriter
from mrok.logging import setup_logging
from mrok.proxy.ziti import ZitiSocketCache

logger = logging.getLogger("mrok.proxy")


class ProxyError(Exception):
    pass


class ProxyApp(ForwardAppBase):
    def __init__(
        self,
        identity_file: str | Path,
        *,
        read_chunk_size: int = 65536,
    ) -> None:
        super().__init__(read_chunk_size=read_chunk_size)
        self._identity_file = identity_file
        settings = get_settings()
        self._proxy_wildcard_domain = (
            settings.proxy.domain
            if settings.proxy.domain[0] == "."
            else f".{settings.proxy.domain}"
        )
        self._ziti_socket_cache = ZitiSocketCache(self._identity_file)

    def get_target_from_header(self, headers: dict[str, str], name: str) -> str | None:
        header_value = headers.get(name, "")
        if self._proxy_wildcard_domain in header_value:
            if ":" in header_value:
                header_value, _ = header_value.split(":", 1)
            return header_value[: -len(self._proxy_wildcard_domain)]

    def get_target_name(self, headers: dict[str, str]) -> str:
        target = self.get_target_from_header(headers, "x-forwarded-host")
        if not target:
            target = self.get_target_from_header(headers, "host")
        if not target:
            raise ProxyError("Neither Host nor X-Forwarded-Host contain a valid target name")
        return target

    async def startup(self):
        setup_logging(get_settings())

    async def shutdown(self):
        await self._ziti_socket_cache.stop()

    async def select_backend(
        self,
        scope: Scope,
        headers: dict[str, str],
    ) -> tuple[StreamReader, StreamWriter] | tuple[None, None]:
        target_name = self.get_target_name(headers)
        sock = self._ziti_socket_cache.get_or_create(target_name)
        reader, writer = await asyncio.open_connection(sock=sock)
        return reader, writer
