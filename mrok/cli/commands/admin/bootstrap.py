import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated, Any

import typer
from rich import print

from mrok.cli.commands.admin.utils import parse_tags
from mrok.conf import Settings
from mrok.types.ziti import Tags
from mrok.ziti.api import ZitiClientAPI, ZitiManagementAPI
from mrok.ziti.bootstrap import bootstrap_identity

logger = logging.getLogger(__name__)


async def bootstrap(
    settings: Settings, forced: bool, tags: Tags | None
) -> tuple[str, dict[str, Any] | None]:
    async with ZitiManagementAPI(settings) as mgmt_api, ZitiClientAPI(settings) as client_api:
        return await bootstrap_identity(
            mgmt_api,
            client_api,
            settings.frontend.identity,
            settings.frontend.mode,
            forced,
            tags,
        )


def register(app: typer.Typer) -> None:
    @app.command("bootstrap")
    def run_bootstrap(
        ctx: typer.Context,
        identity_file: Path = typer.Argument(
            Path("proxy_identity.json"),
            help="Path to identity output file",
            writable=True,
        ),
        forced: bool = typer.Option(
            False,
            "--force",
            help="Regenerate identity even if it already exists",
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
        """Run the mrok bootstrap."""
        _, identity_json = asyncio.run(bootstrap(ctx.obj, forced, parse_tags(tags)))
        if identity_json:
            json.dump(identity_json, identity_file.open("w"))
            print(
                f"🍻 [green]Ziti bootstrapped, frontend identity saved to"
                f" [bold]{identity_file}[/bold].[/green]"
            )
            return
        print("[light_salmon3]Ziti already bootstrapped[/light_salmon3]")
