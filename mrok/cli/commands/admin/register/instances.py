import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Annotated

import typer

from mrok.ziti.identities import enroll_instance_identity

RE_EXTENSION_ID = re.compile(r"(?i)EXT-\d{4}-\d{4}")


def validate_extension_id(extension_id: str):
    if not RE_EXTENSION_ID.fullmatch(extension_id):
        raise typer.BadParameter("ext_id must match EXT-xxxx-yyyy (case-insensitive)")
    return extension_id


def register(app: typer.Typer) -> None:
    @app.command("instance")
    def create_instance(
        ctx: typer.Context,
        extension_id: str = typer.Argument(
            ..., callback=validate_extension_id, help="Extension ID in format EXT-xxxx-yyyy"
        ),
        instance_uuid: str = typer.Argument(..., help="Instance UUID"),
        output: Annotated[
            Path | None,
            typer.Option(
                "--output",
                "-o",
                file_okay=True,
                dir_okay=False,
                writable=True,
                resolve_path=True,
                help="Output file (default: stdout)",
            ),
        ] = None,
    ):
        """Register a new Extension Instance in OpenZiti (identity)."""
        identity = asyncio.run(enroll_instance_identity(extension_id.lower(), instance_uuid))
        if output:
            json.dump(identity, output.open("w"))
        else:
            sys.stdout.write(json.dumps(identity))
