import logging
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import openziti
from uvicorn import config

from mrok.conf import get_settings
from mrok.http.protocol import MrokHttpToolsProtocol
from mrok.logging import setup_logging

logger = logging.getLogger("mrok.proxy")

config.LIFESPAN["auto"] = "mrok.http.lifespan:MrokLifespan"

ASGIApplication = config.ASGIApplication


class MrokBackendConfig(config.Config):
    def __init__(
        self,
        app: ASGIApplication | Callable[..., Any] | str,
        service_name: str,
        identity_file: str | Path,
        backlog: int = 2048,
    ):
        self.service_name = service_name
        self.identity_file = identity_file
        super().__init__(
            app,
            loop="asyncio",
            http=MrokHttpToolsProtocol,
            backlog=backlog,
        )

    def bind_socket(self) -> socket.socket:
        logger.info(f"Connect to Ziti service '{self.service_name}'")

        ctx, err = openziti.load(str(self.identity_file))
        if err != 0:
            raise RuntimeError(f"Failed to load Ziti identity from {self.identity_file}: {err}")

        sock = ctx.bind(self.service_name)
        sock.listen(self.backlog)
        logger.info(f"listening on ziti service {self.service_name} for connections")
        return sock

    def configure_logging(self) -> None:
        setup_logging(get_settings())
