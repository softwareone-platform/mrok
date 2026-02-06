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
        ziti_load_timeout_ms: int = 5000,
        server_workers: int = 4,
        server_backlog: int = 2048,
        server_timeout_keep_alive: int = 5,
        server_limit_concurrency: int | None = None,
        server_limit_max_requests: int | None = None,
        events_enabled: bool = True,
        events_publishers_port: int = 50000,
        events_subscribers_port: int = 50001,
        events_metrics_collect_interval: float = 5.0,
        upstream_max_connections: int | None = 10,
        upstream_max_keepalive_connections: int | None = None,
        upstream_keepalive_expiry: float | None = None,
        upstream_max_connect_retries: int = 0,
    ):
        super().__init__(
            identity_file,
            ziti_load_timeout_ms=ziti_load_timeout_ms,
            server_workers=server_workers,
            server_reload=False,
            server_backlog=server_backlog,
            server_timeout_keep_alive=server_timeout_keep_alive,
            server_limit_concurrency=server_limit_concurrency,
            server_limit_max_requests=server_limit_max_requests,
            events_enabled=events_enabled,
            events_pub_port=events_publishers_port,
            events_sub_port=events_subscribers_port,
            events_metrics_collect_interval=events_metrics_collect_interval,
        )
        self._target = target
        self._max_connections = upstream_max_connections
        self._max_keepalive_connections = upstream_max_keepalive_connections
        self._keepalive_expiry = upstream_keepalive_expiry
        self._retries = upstream_max_connect_retries

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
    ziti_load_timeout_ms: int = 5000,
    server_workers: int = 4,
    server_backlog: int = 2048,
    server_timeout_keep_alive: int = 5,
    server_limit_concurrency: int | None = None,
    server_limit_max_requests: int | None = None,
    events_enabled: bool = True,
    events_publishers_port: int = 50000,
    events_subscribers_port: int = 50001,
    events_metrics_collect_interval: float = 5.0,
    upstream_max_connections: int | None = 10,
    upstream_max_keepalive_connections: int | None = None,
    upstream_keepalive_expiry: float | None = None,
    upstream_max_connect_retries: int = 0,
):
    agent = SidecarAgent(
        identity_file,
        target_addr,
        ziti_load_timeout_ms=ziti_load_timeout_ms,
        server_workers=server_workers,
        server_backlog=server_backlog,
        server_timeout_keep_alive=server_timeout_keep_alive,
        server_limit_concurrency=server_limit_concurrency,
        server_limit_max_requests=server_limit_max_requests,
        events_enabled=events_enabled,
        events_publishers_port=events_publishers_port,
        events_subscribers_port=events_subscribers_port,
        events_metrics_collect_interval=events_metrics_collect_interval,
        upstream_max_connections=upstream_max_connections,
        upstream_max_keepalive_connections=upstream_max_keepalive_connections,
        upstream_keepalive_expiry=upstream_keepalive_expiry,
        upstream_max_connect_retries=upstream_max_connect_retries,
    )
    agent.run()
