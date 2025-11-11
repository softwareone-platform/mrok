#!/usr/bin/env python3
"""mrok agent devtools CLI entrypoint.

Provides a small CLI that accepts an optional subscriber port and
invokes the `run` function with that port.
"""

import argparse
from typing import Any


def run(port: int) -> None:
    """Run the devtools agent using the given subscriber port.

    This is a stub for the runtime function. Implementation goes here.
    """
    pass


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


if __name__ == "__main__":
    main()
