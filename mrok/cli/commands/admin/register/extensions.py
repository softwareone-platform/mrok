import asyncio
import re
import sys
from typing import Annotated

import typer
from rich import print

from mrok.cli.commands.admin.register.utils import parse_tags
from mrok.errors import MrokError
from mrok.ziti.services import register_service

RE_EXTENSION_ID = re.compile(r"(?i)EXT-\d{4}-\d{4}")


def validate_extension_id(extension_id: str):
    if not RE_EXTENSION_ID.fullmatch(extension_id):
        raise typer.BadParameter("ext_id must match EXT-xxxx-yyyy (case-insensitive)")
    return extension_id


def register(app: typer.Typer) -> None:
    @app.command("extension")
    def register_extension(
        ctx: typer.Context,
        extension_id: str =  typer.Argument(
            ..., callback=validate_extension_id, help="Extension ID in format EXT-xxxx-yyyy"
        ),
        tags: Annotated[
            list[str] | None,
            typer.Option(
                "--tag",
                "-t",
                help="Add tag",
                show_default=True,
            ),
        ] = None,
    ):
        """Register a new Extension in OpenZiti (service)."""
        asyncio.run(
            register_service(extension_id.lower(), tags=parse_tags(tags))
        )
        print(f"🍻 [green]Extension [bold]{extension_id}[/bold] registered.[/green]")
