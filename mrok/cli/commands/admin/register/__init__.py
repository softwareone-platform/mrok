import typer

from mrok.cli.commands.admin.register import extensions, instances

app = typer.Typer(name="register", help="Register resources into OpenZiti.")

extensions.register(app)
instances.register(app)
