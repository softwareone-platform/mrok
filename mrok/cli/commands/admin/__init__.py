import typer

from mrok.cli.commands.admin import bootstrap
from mrok.cli.commands.admin.list import app as list_app
from mrok.cli.commands.admin.register import app as register_app
from mrok.cli.commands.admin.unregister import app as unregister_app

app = typer.Typer(help="mrok administrative commands.")
app.add_typer(register_app)
app.add_typer(unregister_app)
app.add_typer(list_app)
bootstrap.register(app)
