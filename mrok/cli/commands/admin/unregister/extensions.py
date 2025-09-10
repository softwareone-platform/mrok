import asyncio
import re

import typer

from mrok.ziti.services import unregister_service

RE_EXTENSION_ID = re.compile(r"(?i)EXT-\d{4}-\d{4}")


def validate_extension_id(extension_id: str):
    if not RE_EXTENSION_ID.fullmatch(extension_id):
        raise typer.BadParameter("ext_id must match EXT-xxxx-yyyy (case-insensitive)")
    return extension_id


def register(app: typer.Typer) -> None:
    @app.command("extension")
    def unregister_extension(
        ctx: typer.Context,
        extension_id: str =  typer.Argument(
            ..., callback=validate_extension_id, help="Extension ID in format EXT-xxxx-yyyy"
        ),
    ):
        """Unregister a new Extension in OpenZiti (service)."""
        asyncio.run(
            unregister_service(extension_id.lower())
        )
