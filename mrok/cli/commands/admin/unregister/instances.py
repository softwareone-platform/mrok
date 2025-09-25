import re

import typer

RE_EXTENSION_ID = re.compile(r"(?i)EXT-\d{4}-\d{4}")


def validate_extension_id(extension_id: str):
    if not RE_EXTENSION_ID.fullmatch(extension_id):
        raise typer.BadParameter("ext_id must match EXT-xxxx-yyyy (case-insensitive)")
    return extension_id


def register(app: typer.Typer) -> None:
    @app.command("instance")
    def unregister_instance(
        ctx: typer.Context,
        extension_id: str = typer.Argument(
            ..., callback=validate_extension_id, help="Extension ID in format EXT-xxxx-yyyy"
        ),
        instance_id: str = typer.Argument(..., help="Instance ID"),
    ):
        """Register a new Extension Instance in OpenZiti (identity)."""
        # asyncio.run(do_unregister(ctx.obj, extension_id, instance_id))
