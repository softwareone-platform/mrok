import typer

from mrok.cli.commands.agent.run import asgi
from mrok.cli.commands.agent.run import sidecar as sidecar

app = typer.Typer(name="run", help="Run mrok agent.")
asgi.register(app)
