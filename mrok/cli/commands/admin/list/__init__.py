import typer

from mrok.cli.commands.admin.list import extensions, instances

app = typer.Typer(name="list", help="Show resources in OpenZiti.")

extensions.register(app)
instances.register(app)
