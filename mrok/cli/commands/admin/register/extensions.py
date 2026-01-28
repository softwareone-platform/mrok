import asyncio
from typing import Annotated

import typer
from rich import print

from mrok.cli.commands.admin.utils import parse_tags
from mrok.cli.utils import validate_extension_id
from mrok.conf import Settings, get_settings
from mrok.ziti.api import ZitiManagementAPI
from mrok.ziti.services import register_service


async def do_register(settings: Settings, extension_id: str, tags: list[str] | None):
    async with ZitiManagementAPI(settings) as api:
        await register_service(settings, api, extension_id, tags=parse_tags(tags))


def register(app: typer.Typer) -> None:
    settings = get_settings()

    @app.command("extension")
    def register_extension(
        ctx: typer.Context,
        extension_id: str = typer.Argument(
            ...,
            callback=validate_extension_id,
            help=f"Extension ID in the format {settings.identifiers.extension.format}",
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
