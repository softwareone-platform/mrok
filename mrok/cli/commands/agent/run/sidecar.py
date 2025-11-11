import multiprocessing
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel

from mrok.agent import sidecar
from mrok.agent.sidecar.store import RequestStore, RequestStoreManager
from mrok.cli.commands.agent.utils import (
    get_textual_command,
    inspector_port,
    number_of_workers,
    run_inspect_api,
    run_textual,
    store_api_port,
)
from mrok.cli.rich import get_console
from mrok.conf import get_settings

default_workers = number_of_workers()
default_inspector_port = inspector_port()
default_store_port = store_api_port()


def register(app: typer.Typer) -> None:
    @app.command("sidecar")
    def run_sidecar(
        identity_file: Path = typer.Argument(
            ...,
            help="Identity json file",
        ),
        target: Path = typer.Argument(
            ...,
            help="Target service (host:port or path to unix domain socket)",
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
        inspect: Annotated[
            bool,
            typer.Option(
                "--inspect",
                "-i",
                help="Enable inspection. Default: False",
                show_default=True,
            ),
        ] = False,
        textual_port: Annotated[
            int,
            typer.Option(
                "--inspector-port",
                help=f"Port for Web inspector. Default: {default_inspector_port}",
                show_default=True,
            ),
        ] = default_inspector_port,
        console_mode: Annotated[
            bool,
            typer.Option(
                "--console",
                "-c",
                help="Enable inspector console mode. Default: False",
                show_default=True,
            ),
        ] = False,
    ):
        """Run a Sidecar Proxy to expose a web application through OpenZiti."""
        if ":" in str(target):
            host, port = str(target).split(":", 1)
            target_addr = (host or "127.0.0.1", int(port))
        else:
            target_addr = str(target)  # type: ignore

        if inspect:
            settings = get_settings()
            console = get_console()

            RequestStoreManager.register("RequestStore", RequestStore)
            with RequestStoreManager() as manager:
                request_store = manager.RequestStore()  # type: ignore

                if console_mode:
                    inspector_proc = multiprocessing.Process(
                        target=run_inspect_api,
                        args=(request_store, settings.sidecar.store_port),
                        daemon=True,
                    )
                    inspector_proc.start()
                    console.print(
                        Panel(
                            f"[bold yellow]To open inspector, run in a new terminal:"
                            f"[/bold yellow]\n[bold green]{get_textual_command()}[/bold green]",
                            title="mrok Inspector",
                            border_style="cyan",
                        )
                    )
                else:
                    inspector_proc = multiprocessing.Process(
                        target=run_textual,
                        args=(textual_port, settings.sidecar.store_port, request_store),
                        daemon=True,
                    )
                    inspector_proc.start()
                    console.print(
                        Panel(
                            f"Web inspector running at http://localhost:{textual_port}",
                            title="mrok Web Inspector",
                            border_style="cyan",
                        )
                    )

                try:
                    sidecar.run(
                        str(identity_file),
                        target_addr,
                        workers=workers,
                        reload=reload,
                        store=request_store,
                    )
                finally:
                    if inspector_proc:
                        inspector_proc.terminate()
                        console.print("mrok Inspector stopped")
        else:
            sidecar.run(str(identity_file), target_addr, workers=workers, reload=reload)
