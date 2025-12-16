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
        publishers_port: int = 50000,
        subscribers_port: int = 50001,
    ):
        super().__init__(
            identity_file,
            workers,
            False,
            publishers_port,
            subscribers_port,
        )
        self._target = target

    def get_asgi_app(self):
        return SidecarProxyApp(self._target)


def run(
    identity_file: str,
    target_addr: str | Path | tuple[str, int],
    workers: int = 4,
    publishers_port: int = 50000,
    subscribers_port: int = 50001,
):
    agent = SidecarAgent(
        identity_file,
        target_addr,
        workers=workers,
        publishers_port=publishers_port,
        subscribers_port=subscribers_port,
    )
    agent.run()
