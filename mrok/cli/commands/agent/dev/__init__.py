import typer

from mrok.cli.commands.agent.dev import console, web

app = typer.Typer(name="dev", help="Dev tools for mrok agent.")
console.register(app)
web.register(app)
