from mrok.proxy.master import MasterBase
from mrok.types.proxy import ASGIApp


class ZiticornAgent(MasterBase):
    def __init__(
        self,
        app: ASGIApp | str,
        identity_file: str,
        ziti_load_timeout_ms: int = 5000,
        server_workers: int = 4,
        server_reload: bool = False,
        server_backlog: int = 2048,
        server_timeout_keep_alive: int = 5,
        server_limit_concurrency: int | None = None,
        server_limit_max_requests: int | None = None,
        events_publishers_port: int = 50000,
        events_subscribers_port: int = 5000,
        events_metrics_collect_interval: float = 5.0,
    ):
        super().__init__(
            identity_file,
            ziti_load_timeout_ms=ziti_load_timeout_ms,
            server_workers=server_workers,
            server_reload=server_reload,
            server_backlog=server_backlog,
            server_timeout_keep_alive=server_timeout_keep_alive,
            server_limit_concurrency=server_limit_concurrency,
            server_limit_max_requests=server_limit_max_requests,
            events_pub_port=events_publishers_port,
            events_sub_port=events_subscribers_port,
            events_metrics_collect_interval=events_metrics_collect_interval,
        )
        self.app = app

    def get_asgi_app(self):
        return self.app


def run(
    app: ASGIApp | str,
    identity_file: str,
    ziti_load_timeout_ms: int = 5000,
    server_workers: int = 4,
    server_reload: bool = False,
    server_backlog: int = 2048,
    server_timeout_keep_alive: int = 5,
    server_limit_concurrency: int | None = None,
    server_limit_max_requests: int | None = None,
    events_publishers_port: int = 50000,
    events_subscribers_port: int = 50001,
    events_metrics_collect_interval: float = 5.0,
):
    master = ZiticornAgent(
        app,
        identity_file,
        ziti_load_timeout_ms=ziti_load_timeout_ms,
        server_workers=server_workers,
        server_reload=server_reload,
        server_backlog=server_backlog,
        server_timeout_keep_alive=server_timeout_keep_alive,
        server_limit_concurrency=server_limit_concurrency,
        server_limit_max_requests=server_limit_max_requests,
        events_publishers_port=events_publishers_port,
        events_subscribers_port=events_subscribers_port,
        events_metrics_collect_interval=events_metrics_collect_interval,
    )
    master.run()
