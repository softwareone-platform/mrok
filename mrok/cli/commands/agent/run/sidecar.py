from pathlib import Path
from typing import Annotated

import typer

from mrok.agent import sidecar
from mrok.cli.utils import number_of_workers

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
                help="Number of workers.",
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
        ] = 10,
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
        ] = None,
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
        ] = None,
        retries: Annotated[
            int,
            typer.Option(
                "--max-pool-connect-retries",
                help=(
                    "The duration in seconds that an idle HTTP connection "
                    "may be maintained for before being expired from the pool."
                ),
                show_default=True,
            ),
        ] = 0,
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
        no_events: Annotated[
            bool,
            typer.Option(
                "--no-events",
                help="Disable events. Default: False",
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

        sidecar.run(
            str(identity_file),
            target_addr,
            workers=workers,
            events_enabled=not no_events,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            retries=retries,
            publishers_port=publishers_port,
            subscribers_port=subscribers_port,
        )
