import json
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
import yaml

from mrok.controller.openapi import generate_openapi_spec


class OutputFormat(str, Enum):
    json = "json"
    yaml = "yaml"


def register(app: typer.Typer) -> None:
    @app.command("openapi")
    def generate_spec(
        ctx: typer.Context,
        output: Annotated[
            Path | None,
            typer.Option(
                "--output",
                "-o",
                help="Output file",
            ),
        ] = Path("mrok_openapi_spec.yml"),
        output_format: Annotated[
            OutputFormat,
            typer.Option(
                "--output-format",
                "-f",
                help="Output file format",
            ),
        ] = OutputFormat.yaml,
    ):
        """
        Generates the mrok controller OpenAPI spec file.
        """
        from mrok.controller.app import app

        dump_fn = json.dump if output_format == OutputFormat.json else yaml.dump
        spec = generate_openapi_spec(app, ctx.obj)

        with open(output, "w") as f:  # type: ignore
            dump_fn(spec, f, indent=2)
