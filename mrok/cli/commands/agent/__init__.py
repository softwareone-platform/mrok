import typer

from mrok.cli.commands.agent.run import app as run_app

app = typer.Typer(help="mrok agent commands.")
app.add_typer(run_app)
