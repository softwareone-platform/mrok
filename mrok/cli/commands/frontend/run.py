from pathlib import Path
from typing import Annotated

import typer

from mrok import frontend
from mrok.cli.utils import number_of_workers

default_workers = number_of_workers()


def register(app: typer.Typer) -> None:
    @app.command("run")
    def run_frontend(
        ctx: typer.Context,
        identity_file: Path = typer.Argument(
            ...,
            help="Identity json file",
        ),
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
                "-P",
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
        max_connections: Annotated[
            int,
            typer.Option(
                "--max-pool-connections",
                help=(
                    "The maximum number of concurrent HTTP connections that "
                    "the pool should allow. Any attempt to send a request on a pool that "
                    "would exceed this amount will block until a connection is available."
                ),
                show_default=True,
            ),
        ] = 1000,
        max_keepalive_connections: Annotated[
            int | None,
            typer.Option(
                "--max-pool-keepalive-connections",
                help=(
                    "The maximum number of idle HTTP connections "
                    "that will be maintained in the pool."
                ),
                show_default=True,
            ),
        ] = 100,
        keepalive_expiry: Annotated[
            float | None,
            typer.Option(
                "--max-pool-keepalive-expiry",
                help=(
                    "The duration in seconds that an idle HTTP connection "
                    "may be maintained for before being expired from the pool."
                ),
                show_default=True,
            ),
        ] = 300,
    ):
        """Run the mrok frontend with Gunicorn and Uvicorn workers."""
        frontend.run(
            identity_file,
            host,
            port,
            workers,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )
