import typer

from mrok.cli.commands.proxy import run

app = typer.Typer(help="mrok proxy commands.")
run.register(app)
