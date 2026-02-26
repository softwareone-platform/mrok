from pathlib import Path
from typing import Any

from gunicorn.app.base import BaseApplication
from uvicorn_worker import UvicornWorker

from mrok.authentication import HTTPAuthManager
from mrok.conf import get_settings
from mrok.frontend.app import FrontendProxyApp
from mrok.frontend.middleware import ASGIAuthenticationMiddleware, HealthCheckMiddleware
from mrok.logging import get_logging_config
from mrok.proxy.asgi import ASGIAppWrapper


class MrokUvicornWorker(UvicornWorker):
    CONFIG_KWARGS: dict[str, Any] = {"loop": "asyncio", "http": "auto", "lifespan": "on"}


class StandaloneApplication(BaseApplication):  # pragma: no cover
    def __init__(self, options: dict[str, Any] | None = None):
        self.options = options
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        settings = get_settings()
        auth_manager = HTTPAuthManager(settings.controller.auth)

        frontend_app = FrontendProxyApp(
            str(self.options["mrok"]["identity_file"]),
            max_connections=self.options["mrok"]["max_connections"],
            max_keepalive_connections=self.options["mrok"]["max_keepalive_connections"],
            keepalive_expiry=self.options["mrok"]["keepalive_expiry"],
        )
        app = ASGIAppWrapper(frontend_app)
        app.add_middleware(HealthCheckMiddleware)
        app.add_middleware(
            ASGIAuthenticationMiddleware,
            auth_manager=auth_manager,
        )
        return app


def run(
    identity_file: str | Path,
    host: str,
    port: int,
    workers: int,
    reload: bool,
    max_connections: int | None,
    max_keepalive_connections: int | None,
    keepalive_expiry: float | None,
):
    options = {
        "bind": f"{host}:{port}",
        "workers": workers,
        "worker_class": "mrok.frontend.main.MrokUvicornWorker",
        "logconfig_dict": get_logging_config(get_settings()),
        "reload": reload,
        "mrok": {
            "identity_file": str(identity_file),
            "max_connections": max_connections,
            "max_keepalive_connections": max_keepalive_connections,
            "keepalive_expiry": keepalive_expiry,
        },
    }

    StandaloneApplication(options).run()
