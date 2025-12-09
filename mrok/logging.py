import logging.config

from rich.console import Console
from rich.logging import RichHandler
from textual_serve.server import LogHighlighter

from mrok.conf import Settings


def get_logging_config(settings: Settings, cli_mode: bool = False) -> dict:
    log_level = "DEBUG" if settings.logging.debug else "INFO"
    handler = "rich" if settings.logging.rich else "console"

    if cli_mode:
        mrok_handler = "cli"
    else:
        mrok_handler = handler

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} {name} {levelname} (pid: {process}) {message}",
                "style": "{",
            },
            "rich": {
                "format": "{name} {message}",
                "style": "{",
            },
            "plain": {"format": "%(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "stream": "ext://sys.stderr",
            },
            "cli": {
                "class": "logging.StreamHandler",
                "formatter": "plain",
                "stream": "ext://sys.stdout",
            },
            "rich": {
                "class": "rich.logging.RichHandler",
                "level": log_level,
                "formatter": "rich",
                "log_time_format": lambda x: x.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "rich_tracebacks": True,
            },
        },
        "root": {
            "handlers": ["rich"],
            "level": "WARNING",
        },
        "loggers": {
            "gunicorn.access": {
                "handlers": [handler],
                "level": log_level,
                "propagate": False,
            },
            "gunicorn.error": {
                "handlers": [handler],
                "level": log_level,
                "propagate": False,
            },
            "mrok": {
                "handlers": [mrok_handler],
                "level": log_level,
                "propagate": False,
            },
        },
    }

    return logging_config


def setup_logging(settings: Settings, cli_mode: bool = False) -> None:
    logging_config = get_logging_config(settings, cli_mode)
    logging.config.dictConfig(logging_config)


def setup_inspector_logging(console: Console) -> None:
    logging.basicConfig(
        level="WARNING",
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            RichHandler(
                show_path=False,
                show_time=True,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                highlighter=LogHighlighter(),
                console=console,
            )
        ],
    )
