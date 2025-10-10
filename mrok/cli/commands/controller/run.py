from collections.abc import Callable
from typing import Annotated, Any

import typer
from gunicorn.app.base import BaseApplication

from mrok.cli.utils import number_of_workers
from mrok.controller.app import app as asgi_app
from mrok.logging import get_logging_config


class StandaloneApplication(BaseApplication):  # pragma: no cover
    def __init__(self, application: Callable, options: dict[str, Any] | None = None):
        self.options = options or {}
        self.application = application
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
        return self.application


default_workers = number_of_workers()


def register(app: typer.Typer) -> None:
    @app.command("run")
    def run_controller(
        ctx: typer.Context,
        host: Annotated[
            str,
            typer.Option(
                "--host",
                "-h",
                help="Host to bind to. Default: 127.0.0.1",
                show_default=True,
            ),
        ] = "127.0.0.1",
        port: Annotated[
            int,
            typer.Option(
                "--port",
                "-p",
                help="Port to bind to. Default: 8000",
                show_default=True,
            ),
        ] = 8000,
        workers: Annotated[
            int,
            typer.Option(
                "--workers",
                "-w",
                help=f"Number of workers. Default: {default_workers}",
                show_default=True,
            ),
        ] = default_workers,
        dev: Annotated[
            bool,
            typer.Option(
                "--reload",
                "-r",
                help="Enable auto-reload. Default: False",
                show_default=True,
            ),
        ] = False,
    ):
        """Run the mrok controller with Gunicorn and Uvicorn workers."""
        options = {
            "bind": f"{host}:{port}",
            "workers": workers,
            "worker_class": "uvicorn_worker.UvicornWorker",
            "logconfig_dict": get_logging_config(ctx.obj),
            "reload": dev,
        }
        StandaloneApplication(asgi_app, options).run()
