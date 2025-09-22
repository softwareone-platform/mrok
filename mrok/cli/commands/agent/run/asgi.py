import multiprocessing
from pathlib import Path
from typing import Annotated

import typer

# from app.logging import get_logging_config
from mrok.agent import ziticorn


def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1

default_workers = number_of_workers()

def register(app: typer.Typer) -> None:
    @app.command("asgi")
    def run_asgi(
        ctx: typer.Context,
        app: str =  typer.Argument(
            ..., help="ASGI application",
        ),
        extension_id: str = typer.Argument(
            ..., help="Extension ID",
        ),
        identity_file: Path = typer.Argument(
            ..., help="Identity json file",
        ),
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
    ):
        """Run an ASGI application exposing it through OpenZiti network."""
        ziticorn.run(app, extension_id, str(identity_file), workers=workers, reload=reload)
