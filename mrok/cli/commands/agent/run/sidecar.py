import multiprocessing
from pathlib import Path
from typing import Annotated

import typer

from mrok.agent import sidecar
from mrok.agent.sidecar.store import RequestStore, RequestStoreManager
from mrok.cli.commands.agent.utils import number_of_workers, run_inspect_api, run_textual
from mrok.conf import get_settings

default_workers = number_of_workers()


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
    ):
        """Run a Sidecar Proxy to expose a web application through OpenZiti."""
        if ":" in str(target):
            host, port = str(target).split(":", 1)
            target_addr = (host or "127.0.0.1", int(port))
        else:
            target_addr = str(target)  # type: ignore

        if inspect:
            settings = get_settings()

            RequestStoreManager.register("RequestStore", RequestStore)
            with RequestStoreManager() as manager:
                request_store = manager.RequestStore()  # type: ignore

                api_proc = multiprocessing.Process(
                    target=run_inspect_api,
                    args=(request_store, settings.sidecar.store_port),
                    daemon=True,
                )
                api_proc.start()
                textual_proc = multiprocessing.Process(
                    target=run_textual,
                    args=(settings.sidecar.textual_port,),
                    daemon=True,
                )
                textual_proc.start()
                typer.echo(f"Inspector running at http://localhost:{settings.sidecar.textual_port}")

                try:
                    sidecar.run(
                        str(identity_file),
                        target_addr,
                        workers=workers,
                        reload=reload,
                        store=request_store,
                    )
                finally:
                    if textual_proc:
                        textual_proc.terminate()
                        typer.echo("Inspector stopped")
                    if api_proc:
                        api_proc.terminate()
                        typer.echo("Inspector store stopped")
        else:
            sidecar.run(str(identity_file), target_addr, workers=workers, reload=reload)
