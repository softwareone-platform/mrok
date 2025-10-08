import asyncio
from typing import Annotated

import typer
from rich import box
from rich.table import Table

from mrok.cli.commands.admin.utils import (
    extract_names,
    format_tags,
    format_timestamp,
    tags_to_filter,
)
from mrok.cli.rich import get_console
from mrok.conf import Settings
from mrok.ziti.api import ZitiManagementAPI


async def get_extensions(
    settings: Settings, detailed: bool, tags: list[str] | None = None
) -> list[dict]:
    async with ZitiManagementAPI(settings) as api:
        if tags is None:
            params = None
        else:
            params = {"filter": tags_to_filter(tags)}

        services = [service async for service in api.services(params=params)]
        if detailed:
            for service in services:
                service["configs"] = [
                    config
                    async for config in api.collection_iterator(
                        f"/services/{service['id']}/configs",
                    )
                ]
                service["policies"] = [
                    policy
                    async for policy in api.collection_iterator(
                        f"/services/{service['id']}/service-policies",
                    )
                ]
        return services


def render_tsv(extensions: list[dict], detailed: bool) -> None:
    console = get_console()
    if detailed:
        console.print("id\tname\tconfigurations\tpolicies\ttags\tcreated\tupdated")
        for extension in extensions:
            console.print(
                f"{extension['id']}\t{extension['name']}\t"
                f"{extract_names(extension['configs'], ', ')}\t"
                f"{extract_names(extension['policies'], ', ')}\t"
                f"{format_tags(extension['tags'], ', ')}\t"
                f"{format_timestamp(extension['createdAt'])}\t"
                f"{format_timestamp(extension['updatedAt'])}"
            )
    else:
        console.print("id\tname\ttags\tcreated")
        for extension in extensions:
            console.print(
                f"{extension['id']}\t{extension['name']}\t"
                f"{format_tags(extension['tags'], ', ')}\t"
                f"{format_timestamp(extension['createdAt'])}\t"
            )


def render_table(extensions: list[dict], detailed: bool) -> None:
    table = Table(
        box=box.ROUNDED,
        title="🔍 Extensions in OpenZiti (services):",
        title_justify="left",
        border_style="#472AFF",
        show_lines=True,
    )
    table.add_column("Id", style="green")
    table.add_column("Name", style="bold cyan")
    if detailed:
        table.add_column("Configurations")
        table.add_column("Service Policies")
    table.add_column("Tags")
    table.add_column("Created", style="dim")
    if detailed:
        table.add_column("Updated", style="dim")

    for extension in extensions:
        row = [
            extension["id"],
            extension["name"],
        ]
        if detailed:
            row += [
                extract_names(extension["configs"]),
                extract_names(extension["policies"]),
            ]
        row += [
            format_tags(extension["tags"]),
            format_timestamp(extension["createdAt"]),
        ]
        if detailed:
            row.append(format_timestamp(extension["updatedAt"]))

        table.add_row(*row)

    get_console().print(table)


def register(app: typer.Typer) -> None:
    @app.command("extensions")
    def list_extensions(
        ctx: typer.Context,
        detailed: bool = typer.Option(
            False,
            "--detailed",
            "-d",
            help="Output detailed information",
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
        tsv_output: bool = typer.Option(
            False,
            "--tsv",
            help="Output as TSV",
        ),
    ):
        """List extensions in OpenZiti (service)."""
        extensions = asyncio.run(get_extensions(ctx.obj, detailed, tags))

        if len(extensions) == 0:
            get_console().print("No extensions found.")
            return

        if tsv_output:
            render_tsv(extensions, detailed)
        else:
            render_table(extensions, detailed)
