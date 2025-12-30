import logging
from pathlib import Path
from typing import Literal

from httpcore import AsyncConnectionPool

from mrok.proxy.app import ProxyAppBase
from mrok.types.proxy import Scope

logger = logging.getLogger("mrok.agent")


TargetType = Literal["tcp", "unix"]


class SidecarProxyApp(ProxyAppBase):
    def __init__(
        self,
        target: str | Path | tuple[str, int],
        *,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        retries: int = 0,
    ):
        self._target = target
        self._target_type, self._target_address = self._parse_target()
        super().__init__(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            retries=retries,
        )

    def setup_connection_pool(
        self,
        max_connections: int | None,
        max_keepalive_connections: int | None,
        keepalive_expiry: float | None,
        retries: int,
    ) -> AsyncConnectionPool:
        if self._target_type == "unix":
            return AsyncConnectionPool(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
                keepalive_expiry=keepalive_expiry,
                retries=retries,
                uds=self._target_address,
            )
        return AsyncConnectionPool(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            retries=retries,
        )

    def get_upstream_base_url(self, scope: Scope) -> str:
        if self._target_type == "unix":
            return "http://localhost"
        return f"http://{self._target_address}"

    def _parse_target(self) -> tuple[TargetType, str]:
        if isinstance(self._target, Path) or (
            isinstance(self._target, str) and ":" not in self._target
        ):
            return "unix", str(self._target)

        if isinstance(self._target, str) and ":" in self._target:
            host, port = str(self._target).split(":", 1)
            host = host or "127.0.0.1"
        elif isinstance(self._target, tuple) and len(self._target) == 2:
            host = self._target[0]
            port = str(self._target[1])
        else:
            raise Exception(f"Invalid target address: {self._target}")

        return "tcp", f"{host}:{port}"
