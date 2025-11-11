from typing import Annotated

import typer

from mrok.agent.devtools.inspector.app import InspectorApp


def register(app: typer.Typer) -> None:
    @app.command("console")
    def run_dev_console(
        subscriber_port: Annotated[
            int,
            typer.Option(
                "--subscriber-port",
                "-s",
                help=(
                    "TCP port where the mrok inspector console application "
                    "should connect to subscribe to request/response messages."
                ),
                show_default=True,
            ),
        ] = 50001,
    ):
        app = InspectorApp(subscriber_port)
        app.run()
