import argparse
from typing import Any

from mrok.agent.devtools.inspector.app import InspectorApp


def run(port: int) -> None:
    app = InspectorApp(port)
    app.run()


def main(argv: Any = None) -> None:
    parser = argparse.ArgumentParser(description="mrok devtools agent")
    parser.add_argument(
        "-p",
        "--subscriber-port",
        type=int,
        default=50001,
        help="Port for subscriber (default: 50001)",
    )
    args = parser.parse_args(argv)
    run(args.subscriber_port)


main()
