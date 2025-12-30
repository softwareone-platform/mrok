import json
import logging
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import openziti
from uvicorn import config, server
from uvicorn.lifespan.on import LifespanOn
from uvicorn.protocols.http.httptools_impl import HttpToolsProtocol as UvHttpToolsProtocol

from mrok.types.proxy import ASGIApp

logger = logging.getLogger("mrok.proxy")

config.LIFESPAN["auto"] = "mrok.proxy.ziticorn:Lifespan"


class Lifespan(LifespanOn):
    def __init__(self, lf_config: config.Config) -> None:
        super().__init__(lf_config)
        self.logger = logging.getLogger("mrok.proxy")


class HttpToolsProtocol(UvHttpToolsProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("mrok.proxy")
        self.access_logger = logging.getLogger("mrok.access")
        self.access_log = self.access_logger.hasHandlers()


class Server(server.Server):
    async def serve(self, sockets: list[socket.socket] | None = None) -> None:
        if not sockets:
            sockets = [self.config.bind_socket()]
        with self.capture_signals():
            await self._serve(sockets)


class BackendConfig(config.Config):
    def __init__(
        self,
        app: ASGIApp | Callable[..., Any] | str,
        identity_file: str | Path,
        ziti_load_timeout_ms: int = 5000,
        backlog: int = 2048,
    ):
        self.identity_file = identity_file
        self.ziti_load_timeout_ms = ziti_load_timeout_ms
        self.service_name, self.identity_name, self.instance_id = self.get_identity_info(
            identity_file
        )
        super().__init__(
            app,
            loop="asyncio",
            http=HttpToolsProtocol,
            backlog=backlog,
        )

    def get_identity_info(self, identity_file: str | Path):
        with open(identity_file) as f:
            identity_data = json.load(f)
            try:
                identity_name = identity_data["mrok"]["identity"]
                instance_id, service_name = identity_name.split(".", 1)
                return service_name, identity_name, instance_id
            except KeyError:
                raise ValueError("Invalid identity file: identity file is not mrok compatible.")

    def bind_socket(self) -> socket.socket:
        logger.info(f"Connect to Ziti service '{self.service_name} ({self.instance_id})'")

        ctx, err = openziti.load(str(self.identity_file), timeout=self.ziti_load_timeout_ms)
        if err != 0:
            raise RuntimeError(f"Failed to load Ziti identity from {self.identity_file}: {err}")

        sock = ctx.bind(self.service_name)
        sock.listen(self.backlog)
        logger.info(f"listening on ziti service {self.service_name} for connections")
        return sock

    def configure_logging(self) -> None:
        return
