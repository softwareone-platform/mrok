import asyncio
from typing import Annotated

import typer
from rich import print

from mrok.cli.commands.admin.utils import parse_tags
from mrok.conf import Settings
from mrok.constants import RE_EXTENSION_ID
from mrok.ziti.api import ZitiManagementAPI
from mrok.ziti.services import register_service


async def do_register(settings: Settings, extension_id: str, tags: list[str] | None):
    async with ZitiManagementAPI(settings) as api:
        await register_service(settings, api, extension_id, tags=parse_tags(tags))


def validate_extension_id(extension_id: str) -> str:
    if not RE_EXTENSION_ID.fullmatch(extension_id):
        raise typer.BadParameter("it must match EXT-xxxx-yyyy (case-insensitive)")
    return extension_id


def register(app: typer.Typer) -> None:
    @app.command("extension")
    def register_extension(
        ctx: typer.Context,
        extension_id: str = typer.Argument(
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
        asyncio.run(do_register(ctx.obj, extension_id, tags))
        print(f"🍻 [green]Extension [bold]{extension_id}[/bold] registered.[/green]")
