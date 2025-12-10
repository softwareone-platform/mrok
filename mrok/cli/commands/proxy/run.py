from pathlib import Path
from typing import Annotated

import typer

from mrok import proxy
from mrok.cli.utils import number_of_workers

default_workers = number_of_workers()


def register(app: typer.Typer) -> None:
    @app.command("run")
    def run_proxy(
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
    ):
        """Run the mrok proxy with Gunicorn and Uvicorn workers."""
        proxy.run(identity_file, host, port, workers)
