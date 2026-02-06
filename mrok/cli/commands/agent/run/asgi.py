from pathlib import Path
from typing import Annotated

import typer

from mrok.agent import ziticorn
from mrok.cli.utils import number_of_workers

default_workers = number_of_workers()


def register(app: typer.Typer) -> None:
    @app.command("asgi")
    def run_asgi(
        identity_file: Annotated[Path, typer.Argument(..., help="Identity json file")],
        app: Annotated[str, typer.Argument(..., help="ASGI application")],
        workers: Annotated[
            int,
            typer.Option(
                "--workers",
                "-w",
                help=f"Number of workers. Default: {default_workers}",
                show_default=True,
            ),
        ] = default_workers,
        reload: Annotated[
            bool,
            typer.Option(
                "--reload",
                "-r",
                help="Enable auto-reload. Default: False",
                show_default=True,
            ),
        ] = False,
        publishers_port: Annotated[
            int,
            typer.Option(
                "--publishers-port",
                "-p",
                help=(
                    "TCP port where the mrok agent "
                    "should connect to publish to request/response messages."
                ),
                show_default=True,
            ),
        ] = 50000,
        subscribers_port: Annotated[
            int,
            typer.Option(
                "--subscribers-port",
                "-s",
                help=(
                    "TCP port where the mrok agent should listen for incoming subscribers "
                    "connections for request/response messages."
                ),
                show_default=True,
            ),
        ] = 50001,
        ziti_load_timeout_ms: Annotated[
            int,
            typer.Option(
                "--ziti-load-timeout-ms",
                help="Timeout (ms) waiting for Ziti to load.",
                show_default=True,
            ),
        ] = 5000,
        backlog: Annotated[
            int,
            typer.Option(
                "--backlog",
                help="TCP socket listen backlog.",
                show_default=True,
            ),
        ] = 2048,
        timeout_keep_alive: Annotated[
            int,
            typer.Option(
                "--timeout-keep-alive",
                help="Seconds to keep idle HTTP connections open.",
                show_default=True,
            ),
        ] = 5,
        limit_concurrency: Annotated[
            int,
            typer.Option(
                "--limit-concurrency",
                help="Maximum number of concurrent requests per worker.",
                show_default=True,
            ),
        ] = None,
        limit_max_requests: Annotated[
            int,
            typer.Option(
                "--limit-max-requests",
                help="Restart a worker after handling this many requests.",
                show_default=True,
            ),
        ] = 5000,
    ):
        """Run an ASGI application exposing it through OpenZiti network."""
        ziticorn.run(
            app,
            str(identity_file),
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
