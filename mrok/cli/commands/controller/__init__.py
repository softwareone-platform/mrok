import typer

from mrok.cli.commands.controller import openapi, run

app = typer.Typer(help="mrok controller commands.")
run.register(app)
openapi.register(app)
