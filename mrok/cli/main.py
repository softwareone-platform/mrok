import inspect
import sys

import typer
from pyfiglet import Figlet
from rich.text import Text
from typer.core import TyperGroup

from mrok.cli import commands
from mrok.cli.rich import get_console
from mrok.conf import get_settings
from mrok.logging import setup_logging


def gradient(start_hex, end_hex, num_samples=10):
    start_rgb = tuple(int(start_hex[i : i + 2], 16) for i in range(1, 6, 2))
    end_rgb = tuple(int(end_hex[i : i + 2], 16) for i in range(1, 6, 2))
    gradient_colors = [start_hex]
    for sample in range(1, num_samples):
        red = int(start_rgb[0] + (float(sample) / (num_samples - 1)) * (end_rgb[0] - start_rgb[0]))
        green = int(
            start_rgb[1] + (float(sample) / (num_samples - 1)) * (end_rgb[1] - start_rgb[1])
        )
        blue = int(start_rgb[2] + (float(sample) / (num_samples - 1)) * (end_rgb[2] - start_rgb[2]))
        gradient_colors.append(f"#{red:02X}{green:02X}{blue:02X}")

    return gradient_colors


def show_banner():
    program_name = "mrok"
    figlet = Figlet("georgia11")

    banner_text = figlet.renderText(program_name)

    banner_lines = [Text(line) for line in banner_text.splitlines()]
    max_line_length = max(len(line) for line in banner_lines)
    half_length = max_line_length // 2

    colors = gradient("#00C9CD", "#472AFF", half_length) + gradient(
        "#472AFF", "#392D9C", half_length + 1
    )
    console = get_console()

    for line in banner_lines:
        colored_line = Text()
        for i in range(len(line)):
            char = line[i : i + 1]
            char.stylize(colors[i])
            colored_line = Text.assemble(colored_line, char)
        console.print(colored_line)


class MrokGroup(TyperGroup):
    def get_help(self, ctx):
        show_banner()
        return super().get_help(ctx)

    def invoke(self, ctx):
        show_banner()
        return super().invoke(ctx)


app = typer.Typer(
    help="SoftwareOne Marketplace Extension Channel CLI",
    add_completion=True,
    rich_markup_mode="rich",
    cls=MrokGroup,
)

err_console = get_console(stderr=True)

for name, module in inspect.getmembers(commands):
    if not inspect.ismodule(module):
        continue

    if hasattr(module, "command"):  # pragma: no branch
        app.command(name=name.replace("_", "-"))(module.command)
    elif hasattr(module, "app"):  # pragma: no branch
        app.add_typer(module.app, name=name.replace("_", "-"))


@app.callback()
def main(
    ctx: typer.Context,
):
    settings = get_settings()
    setup_logging(settings, cli_mode=True)
    ctx.obj = settings


def run():
    try:
        app()
    except Exception as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(-1)
