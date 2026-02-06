import asyncio

import typer

from mrok.cli.utils import validate_extension_id
from mrok.conf import Settings, get_settings
from mrok.ziti.api import ZitiManagementAPI
from mrok.ziti.services import unregister_service


async def do_unregister(settings: Settings, extension_id: str):
    async with ZitiManagementAPI(settings) as api:
        await unregister_service(settings, api, extension_id)


def register(app: typer.Typer) -> None:
    settings = get_settings()

    @app.command("extension")
    def unregister_extension(
        ctx: typer.Context,
        extension_id: str = typer.Argument(
            ...,
            callback=validate_extension_id,
            help=f"Extension ID in the format {settings.identifiers.extension.format}",
        ),
    ):
        """Unregister a new Extension in OpenZiti (service)."""
        asyncio.run(do_unregister(ctx.obj, extension_id))
        print(f"🍻 [green]Extension [bold]{extension_id}[/bold] unregistered.[/green]")
