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
from mrok.ziti.constants import (
    MROK_IDENTITY_TYPE_TAG_NAME,
    MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE,
)


async def get_instances(
    settings: Settings, detailed: bool, extension: str | None = None, tags: list[str] | None = None
) -> list[dict]:
    async with ZitiManagementAPI(settings) as api:
        tags = tags or []
        tags.append(f"{MROK_IDENTITY_TYPE_TAG_NAME}={MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE}")
        identities = [
            identity async for identity in api.identities(params={"filter": tags_to_filter(tags)})
        ]
        if detailed or extension:
            for identity in identities:
                identity["services"] = [
                    service
                    async for service in api.collection_iterator(
                        f"/identities/{identity['id']}/services"
                    )
                ]
                identity["policies"] = [
                    policy
                    async for policy in api.collection_iterator(
                        f"/identities/{identity['id']}/service-policies"
                    )
                ]

        if extension:
            return [
                identity
                for identity in identities
                if any(
                    service["id"] == extension or service["name"] == extension
                    for service in identity["services"]
                )
            ]

        return identities


def render_tsv(instances: list[dict], detailed: bool) -> None:
    console = get_console()
    if detailed:
        console.print("id\tname\tservices\tpolicies\ttags\tcreated\tupdated")
        for instance in instances:
            console.print(
                f"{instance['id']}\t{instance['name']}\t"
                f"{extract_names(instance['services'], ', ')}\t"
                f"{extract_names(instance['policies'], ', ')}\t"
                f"{format_tags(instance['tags'], ', ')}\t"
                f"{format_timestamp(instance['createdAt'])}\t"
                f"{format_timestamp(instance['updatedAt'])}"
            )
    else:
        console.print("id\tname\ttags\tcreated")
        for instance in instances:
            console.print(
                f"{instance['id']}\t{instance['name']}\t"
                f"{format_tags(instance['tags'], ', ')}\t"
                f"{format_timestamp(instance['createdAt'])}\t"
            )


def render_table(instances: list[dict], detailed: bool) -> None:
    table = Table(
        box=box.ROUNDED,
        title="🔍 Instances in OpenZiti (identities):",
        title_justify="left",
        border_style="#472AFF",
        show_lines=True,
    )
    table.add_column("Id", style="green")
    table.add_column("Name", style="bold cyan")
    if detailed:
        table.add_column("Associated services")
        table.add_column("Associated service policies")
    table.add_column("Tags")
    table.add_column("Created", style="dim")
    if detailed:
        table.add_column("Updated", style="dim")

    for instance in instances:
        row = [
            instance["id"],
            instance["name"],
        ]
        if detailed:
            row += [
                extract_names(instance["services"]),
                extract_names(instance["policies"]),
            ]
        row += [
            format_tags(instance["tags"]),
            format_timestamp(instance["createdAt"]),
        ]
        if detailed:
            row.append(format_timestamp(instance["updatedAt"]))

        table.add_row(*row)

    get_console().print(table)


def register(app: typer.Typer) -> None:
    @app.command("instances")
    def list_instances(
        ctx: typer.Context,
        extension: Annotated[
            str | None,
            typer.Option(
                "--extension",
                "-e",
                help="Filter instances by extension",
                show_default=True,
            ),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option(
                "--tag",
                "-t",
                help="Add tag",
                show_default=True,
            ),
        ] = None,
        detailed: bool = typer.Option(
            False,
            "--detailed",
            "-d",
            help="Output detailed information",
        ),
        tsv_output: bool = typer.Option(
            False,
            "--tsv",
            help="Output as TSV",
        ),
    ):
        """List instances in OpenZiti (identities)."""
        instances = asyncio.run(get_instances(ctx.obj, detailed, extension, tags))

        if len(instances) == 0:
            get_console().print("No instances found.")
            return

        if tsv_output:
            render_tsv(instances, detailed)
        else:
            render_table(instances, detailed)
