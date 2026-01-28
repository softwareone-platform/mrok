import asyncio

import typer

from mrok.cli.utils import validate_extension_id, validate_instance_id
from mrok.conf import Settings, get_settings
from mrok.ziti.api import ZitiManagementAPI
from mrok.ziti.identities import unregister_identity


async def do_unregister(settings: Settings, extension_id: str, instance_id: str):
    async with ZitiManagementAPI(settings) as api:
        await unregister_identity(settings, api, extension_id, instance_id)


def register(app: typer.Typer) -> None:
    settings = get_settings()

    @app.command("instance")
    def unregister_instance(
        ctx: typer.Context,
        extension_id: str = typer.Argument(
            ...,
            callback=validate_extension_id,
            help=f"Extension ID in the format {settings.identifiers.extension.format}",
        ),
        instance_id: str = typer.Argument(
            ...,
            callback=validate_instance_id,
            help=f"Instance ID in the format {settings.identifiers.instance.format}",
        ),
    ):
        """Register a new Extension Instance in OpenZiti (identity)."""
        asyncio.run(do_unregister(ctx.obj, extension_id, instance_id))
