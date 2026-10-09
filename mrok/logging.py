import logging
import logging.config

from mrok.conf import Settings

ACCESS_LOG_FORMAT = "{asctime} {name} {levelname} (pid: {process}) [{request_target}] {message}"


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return "/healthcheck" not in record.getMessage()


def get_logging_config(settings: Settings, cli_mode: bool = False) -> dict:
    log_level = "DEBUG" if settings.logging.debug else "INFO"
    handler = "rich" if settings.logging.rich else "console"
    access_handler = "rich" if settings.logging.rich else "access"

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
            "access": {
                "format": ACCESS_LOG_FORMAT,
                "style": "{",
                "defaults": {"request_target": "-"},
            },
        },
        "filters": {
            "healthcheck_filter": {
                "()": HealthCheckFilter,
            },
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
            "access": {
                "class": "logging.StreamHandler",
                "formatter": "access",
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "handlers": [handler],
            "level": "WARNING",
        },
        "loggers": {
            "gunicorn.access": {
                "handlers": [access_handler],
                "level": log_level,
                "propagate": False,
                "filters": ["healthcheck_filter"],
            },
            "gunicorn.error": {
                "handlers": [handler],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": [access_handler],
                "level": log_level,
                "propagate": False,
                "filters": ["healthcheck_filter"],
            },
            "mrok": {
                "handlers": [mrok_handler],
                "level": log_level,
                "propagate": False,
            },
            "mrok.access": {
                "handlers": [mrok_handler],
                "level": log_level,
                "propagate": False,
                "filters": ["healthcheck_filter"],
            },
            "httpcore": {
                "handlers": [mrok_handler],
                "level": log_level,
                "propagate": False,
            },
        },
    }

    return logging_config


def setup_logging(
    settings: Settings, cli_mode: bool = False, logging_config: dict | None = None
) -> None:
    logging_config = logging_config or get_logging_config(settings, cli_mode)
    logging.config.dictConfig(logging_config)
