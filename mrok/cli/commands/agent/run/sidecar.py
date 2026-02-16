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
        ziti_load_timeout_ms: Annotated[
            int,
            typer.Option(
                "--ziti-load-timeout-ms",
                help="Timeout (ms) waiting for Ziti to load.",
                show_default=True,
            ),
        ] = 5000,
        server_workers: Annotated[
            int,
            typer.Option(
                "--server-workers",
                "-w",
                help="Number of workers.",
                show_default=True,
            ),
        ] = default_workers,
        server_backlog: Annotated[
            int,
            typer.Option(
                "--server-backlog",
                help="TCP socket listen backlog.",
                show_default=True,
            ),
        ] = 2048,
        server_timeout_keep_alive: Annotated[
            int,
            typer.Option(
                "--server-timeout-keep-alive",
                help="Seconds to keep idle HTTP connections open.",
                show_default=True,
            ),
        ] = 5,
        server_limit_concurrency: Annotated[
            int | None,
            typer.Option(
                "--server-limit-concurrency",
                help="Maximum number of concurrent requests per worker.",
                show_default=True,
            ),
        ] = None,
        server_limit_max_requests: Annotated[
            int | None,
            None,
            typer.Option(
                "--server-limit-max-requests",
                help="Restart a worker after handling this many requests.",
                show_default=True,
            ),
        ] = None,
        events_publishers_port: Annotated[
            int,
            typer.Option(
                "--events-publishers-port",
                "-p",
                help="TCP port where the mrok agent should connect to publish events.",
                show_default=True,
            ),
        ] = 50000,
        events_subscribers_port: Annotated[
            int,
            typer.Option(
                "--events-subscribers-port",
                help=(
                    "TCP port where the mrok agent should listen for incoming subscribers "
                    "connections for listening to events."
                ),
                show_default=True,
            ),
        ] = 50001,
        events_metrics_collect_interval: Annotated[
            float,
            typer.Option(
                "--events-metrics-collect-interval",
                help="Interval in seconds between events metrics collect.",
                show_default=True,
            ),
        ] = 5.0,
        no_events: Annotated[
            bool,
            typer.Option(
                "--no-events",
                help="Disable events. Default: False",
                show_default=True,
            ),
        ] = False,
        upstream_max_connections: Annotated[
            int,
            typer.Option(
                "--upstream-max-connections",
                help=(
                    "The maximum number of concurrent HTTP connections to the target service that "
                    "the pool should allow. Any attempt to send a request on "
                    "a pool that would exceed this amount will block until a connection "
                    "is available."
                ),
                show_default=True,
            ),
        ] = 10,
        upstream_max_keepalive_connections: Annotated[
            int | None,
            typer.Option(
                "--upstream-max-keepalive-connections",
                help=(
                    "The maximum number of idle HTTP connections "
                    "that will be maintained in the connection pool to the "
                    "target service."
                ),
                show_default=True,
            ),
        ] = None,
        upstream_keepalive_expiry: Annotated[
            float | None,
            typer.Option(
                "--upstream_keepalive_expiry",
                help=(
                    "The duration in seconds that an idle HTTP connection to the target service"
                    "may be maintained for before being expired from the pool."
                ),
                show_default=True,
            ),
        ] = None,
        upstream_max_connect_retries: Annotated[
            int,
            typer.Option(
                "--upstream-max-connect-retries",
                help=(
                    "The duration in seconds that an idle HTTP connection to the target service"
                    "may be maintained for before being expired from the pool."
                ),
                show_default=True,
            ),
        ] = 0,
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
            ziti_load_timeout_ms=ziti_load_timeout_ms,
            server_workers=server_workers,
            server_backlog=server_backlog,
            server_timeout_keep_alive=server_timeout_keep_alive,
            server_limit_concurrency=server_limit_concurrency,
            server_limit_max_requests=server_limit_max_requests,
            events_enabled=not no_events,
            events_publishers_port=events_publishers_port,
            events_subscribers_port=events_subscribers_port,
            events_metrics_collect_interval=events_metrics_collect_interval,
            upstream_max_connections=upstream_max_connections,
            upstream_max_keepalive_connections=upstream_max_keepalive_connections,
            upstream_keepalive_expiry=upstream_keepalive_expiry,
            upstream_max_connect_retries=upstream_max_connect_retries,
        )
