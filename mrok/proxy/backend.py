import asyncio
from collections.abc import Iterable
from pathlib import Path

import openziti
from httpcore import SOCKET_OPTION, AsyncNetworkBackend, AsyncNetworkStream
from openziti.context import ZitiContext

from mrok.proxy.exceptions import InvalidTargetError, TargetUnavailableError
from mrok.proxy.stream import AIONetworkStream


class AIOZitiNetworkBackend(AsyncNetworkBackend):
    def __init__(self, identity_file: str | Path) -> None:
        self._identity_file = identity_file
        self._ziti_ctx: ZitiContext | None = None

    def _get_ziti_ctx(self) -> ZitiContext:
        if self._ziti_ctx is None:
            ctx, err = openziti.load(str(self._identity_file), timeout=10_000)
            if err != 0:
                raise Exception(f"Cannot create a Ziti context from the identity file: {err}")
            self._ziti_ctx = ctx
        return self._ziti_ctx

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SOCKET_OPTION] | None = None,
    ) -> AsyncNetworkStream:
        ctx = self._get_ziti_ctx()
        try:
            sock = ctx.connect(host)
            reader, writer = await asyncio.open_connection(sock=sock)
            return AIONetworkStream(reader, writer)
        except Exception as e:
            if e.args and e.args[0] == -24:  # the service exists but is not available
                raise TargetUnavailableError() from e
            raise InvalidTargetError() from e

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
