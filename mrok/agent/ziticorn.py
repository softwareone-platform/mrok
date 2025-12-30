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
        subscribers_port: int = 50001,
    ):
        super().__init__(
            identity_file,
            workers=workers,
            reload=reload,
            events_pub_port=publishers_port,
            events_sub_port=subscribers_port,
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
):
    master = ZiticornAgent(
        app,
        identity_file,
        workers=workers,
        reload=reload,
        publishers_port=publishers_port,
        subscribers_port=subscribers_port,
    )
    master.run()
