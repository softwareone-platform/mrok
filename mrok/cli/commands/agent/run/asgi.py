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
        app: str = typer.Argument(
            ...,
            help="ASGI application",
        ),
        identity_file: Path = typer.Argument(
            ...,
            help="Identity json file",
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
        ziticorn.run(app, str(identity_file), workers=workers, reload=reload)
