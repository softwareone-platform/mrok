import asyncio
import json
import re
from pathlib import Path
from typing import Annotated

import typer

from mrok.cli.commands.admin.utils import parse_tags
from mrok.conf import Settings
from mrok.ziti.api import ZitiClientAPI, ZitiManagementAPI
from mrok.ziti.identities import register_instance

RE_EXTENSION_ID = re.compile(r"(?i)EXT-\d{4}-\d{4}")


async def do_register(
    settings: Settings, extension_id: str, instance_id: str, tags: list[str] | None
):
    async with ZitiManagementAPI(settings) as mgmt_api, ZitiClientAPI(settings) as client_api:
        return await register_instance(
            mgmt_api, client_api, extension_id, instance_id, tags=parse_tags(tags)
        )


def validate_extension_id(extension_id: str):
    if not RE_EXTENSION_ID.fullmatch(extension_id):
        raise typer.BadParameter("ext_id must match EXT-xxxx-yyyy (case-insensitive)")
    return extension_id


def register(app: typer.Typer) -> None:
    @app.command("instance")
    def register_instance(
        ctx: typer.Context,
        extension_id: str = typer.Argument(
            ..., callback=validate_extension_id, help="Extension ID in format EXT-xxxx-yyyy"
        ),
        instance_id: str = typer.Argument(..., help="Instance ID"),
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
