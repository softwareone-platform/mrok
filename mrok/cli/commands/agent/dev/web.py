from typing import Annotated

import typer

from mrok.agent.devtools.inspector.server import InspectorServer


def register(app: typer.Typer) -> None:
    @app.command("web")
    def run_web_console(
        port: Annotated[
            int,
            typer.Option(
                "--port",
                "-p",
                help="TCP port where the mrok inspector web application will listen for requests.",
                show_default=True,
            ),
        ] = 7777,
        subscriber_port: Annotated[
            int,
            typer.Option(
                "--subscriber-port",
                "-s",
                help=(
                    "TCP port where the mrok inspector web application "
                    "should connect to subscribe to request/response messages."
                ),
                show_default=True,
            ),
        ] = 50001,
    ):
        server = InspectorServer(
            port=port,
            subscriber_port=subscriber_port,
        )
        server.serve()
