import logging
from pathlib import Path

from mrok.agent.sidecar.app import SidecarProxyApp
from mrok.proxy.master import MasterBase

logger = logging.getLogger("mrok.proxy")


class SidecarAgent(MasterBase):
    def __init__(
        self,
        identity_file: str,
        target: str | Path | tuple[str, int],
        workers: int = 4,
        events_enabled: bool = True,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        retries: int = 0,
        publishers_port: int = 50000,
        subscribers_port: int = 50001,
        ziti_load_timeout_ms: int = 5000,
        backlog: int = 2048,
        timeout_keep_alive: int = 5,
        limit_concurrency: int = None,
        limit_max_requests: int = None,
    ):
        super().__init__(
            identity_file,
            workers=workers,
            reload=False,
            events_enabled=events_enabled,
            events_pub_port=publishers_port,
            events_sub_port=subscribers_port,
            ziti_load_timeout_ms=ziti_load_timeout_ms,
            backlog=backlog,
            timeout_keep_alive=timeout_keep_alive,
            limit_concurrency=limit_concurrency,
            limit_max_requests=limit_max_requests,
        )
        self._target = target
        self._max_connections = max_connections
        self._max_keepalive_connections = max_keepalive_connections
        self._keepalive_expiry = keepalive_expiry
        self._retries = retries

    def get_asgi_app(self):
        return SidecarProxyApp(
            self._target,
            max_connections=self._max_connections,
            max_keepalive_connections=self._max_keepalive_connections,
            keepalive_expiry=self._keepalive_expiry,
            retries=self._retries,
        )


def run(
    identity_file: str,
    target_addr: str | Path | tuple[str, int],
    workers: int = 4,
    events_enabled: bool = True,
    max_connections: int | None = 10,
    max_keepalive_connections: int | None = None,
    keepalive_expiry: float | None = None,
    retries: int = 0,
    publishers_port: int = 50000,
    subscribers_port: int = 50001,
    ziti_load_timeout_ms: int = 5000,
    backlog: int = 2048,
    timeout_keep_alive: int = 5,
    limit_concurrency: int | None = None,
    limit_max_requests: int | None = None,
):
    agent = SidecarAgent(
        identity_file,
        target_addr,
        workers=workers,
        events_enabled=events_enabled,
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
        keepalive_expiry=keepalive_expiry,
        retries=retries,
        publishers_port=publishers_port,
        subscribers_port=subscribers_port,
        ziti_load_timeout_ms=ziti_load_timeout_ms,
        backlog=backlog,
        timeout_keep_alive=timeout_keep_alive,
        limit_concurrency=limit_concurrency,
        limit_max_requests=limit_max_requests,
    )
    agent.run()
