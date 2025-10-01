import typer

from mrok.cli.commands.agent.run import asgi, sidecar

app = typer.Typer(name="run", help="Run mrok agent.")
asgi.register(app)
sidecar.register(app)
