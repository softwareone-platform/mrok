import typer

from mrok.cli.commands.admin.unregister import extensions, instances

app = typer.Typer(name="unregister", help="Unregister resources from OpenZiti.")

extensions.register(app)
instances.register(app)
