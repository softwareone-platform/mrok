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
                    "The maximum number of concurrent HTTP connections to the target service that "
                    "the pool should allow. Any attempt to send a request on "
                    "a pool that would exceed this amount will block until a connection "
                    "is available."
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
                    "that will be maintained in the connection pool to the "
                    "target service."
                ),
                show_default=True,
            ),
        ] = None,
        keepalive_expiry: Annotated[
            float | None,
            typer.Option(
                "--max-pool-keepalive-expiry",
                help=(
                    "The duration in seconds that an idle HTTP connection to the target service"
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
                    "The duration in seconds that an idle HTTP connection to the target service"
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
                help=("TCP port where the mrok agent should connect to publish events."),
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
                    "connections for listening to events."
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
            ziti_load_timeout_ms=ziti_load_timeout_ms,
            backlog=backlog,
            timeout_keep_alive=timeout_keep_alive,
            limit_concurrency=limit_concurrency,
            limit_max_requests=limit_max_requests,
        )
