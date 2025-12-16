import typer

from mrok.cli.commands.frontend import run

app = typer.Typer(help="mrok proxy commands.")
run.register(app)
