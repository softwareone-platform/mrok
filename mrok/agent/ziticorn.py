from mrok.proxy.master import MasterBase
from mrok.types.proxy import ASGIApp


class ZiticornAgent(MasterBase):
    def __init__(
        self,
        app: ASGIApp | str,
        identity_file: str,
        workers: int = 4,
        reload: bool = False,
        publishers_port: int = 50000,
        subscribers_port: int = 5000,
        ziti_load_timeout_ms: int = 5000,
        backlog: int = 2048,
        timeout_keep_alive: int = 5,
        limit_concurrency: int = None,
        limit_max_requests: int = None,
    ):
        super().__init__(
            identity_file,
            workers=workers,
            reload=reload,
            events_pub_port=publishers_port,
            events_sub_port=subscribers_port,
            ziti_load_timeout_ms=ziti_load_timeout_ms,
            backlog=backlog,
            timeout_keep_alive=timeout_keep_alive,
            limit_concurrency=limit_concurrency,
            limit_max_requests=limit_max_requests,
        )
        self.app = app

    def get_asgi_app(self):
        return self.app


def run(
    app: ASGIApp | str,
    identity_file: str,
    workers: int = 4,
    reload: bool = False,
    publishers_port: int = 50000,
    subscribers_port: int = 50001,
    ziti_load_timeout_ms: int = 5000,
    backlog: int = 2048,
    timeout_keep_alive: int = 5,
    limit_concurrency: int | None = None,
    limit_max_requests: int | None = None,
):
    master = ZiticornAgent(
        app,
        identity_file,
        workers=workers,
        reload=reload,
        publishers_port=publishers_port,
        subscribers_port=subscribers_port,
        ziti_load_timeout_ms=ziti_load_timeout_ms,
        backlog=backlog,
        timeout_keep_alive=timeout_keep_alive,
        limit_concurrency=limit_concurrency,
        limit_max_requests=limit_max_requests,
    )
    master.run()
