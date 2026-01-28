import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer

from mrok.cli.commands.admin.utils import parse_tags
from mrok.cli.utils import (
    validate_extension_id,
    validate_instance_id,
)
from mrok.conf import Settings, get_settings
from mrok.ziti.api import ZitiClientAPI, ZitiManagementAPI
from mrok.ziti.identities import register_identity


async def do_register(
    settings: Settings, extension_id: str, instance_id: str, tags: list[str] | None
):
    async with ZitiManagementAPI(settings) as mgmt_api, ZitiClientAPI(settings) as client_api:
        return await register_identity(
            settings, mgmt_api, client_api, extension_id, instance_id, tags=parse_tags(tags)
        )


def register(app: typer.Typer) -> None:
    settings = get_settings()

    @app.command("instance")
    def register_instance(
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
        output: Path = typer.Argument(
            ...,
            file_okay=True,
            dir_okay=False,
            writable=True,
            resolve_path=True,
            help="Output file (default: stdout)",
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
        """Register a new Extension Instance in OpenZiti (identity)."""
        _, identity_file = asyncio.run(do_register(ctx.obj, extension_id, instance_id, tags))
        json.dump(identity_file, output.open("w"))
