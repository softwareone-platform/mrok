from pathlib import Path
from typing import Annotated

import typer

from mrok.agent import ziticorn
from mrok.cli.utils import number_of_workers

default_workers = number_of_workers()


def register(app: typer.Typer) -> None:
    @app.command("asgi")
    def run_asgi(
        app: Annotated[str, typer.Argument(..., help="ASGI application")],
        identity_file: Annotated[Path, typer.Argument(..., help="Identity json file")],
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
    ):
        """Run an ASGI application exposing it through OpenZiti network."""
        ziticorn.run(
            app,
            str(identity_file),
            workers=workers,
            reload=reload,
            publishers_port=publishers_port,
            subscribers_port=subscribers_port,
        )
