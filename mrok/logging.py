import logging.config

from mrok.conf import Settings


def get_logging_config(settings: Settings) -> dict:
    log_level = "DEBUG" if settings.logging.debug else "INFO"
    handler = "rich" if settings.logging.rich else "console"
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
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "stream": "ext://sys.stderr",
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
                "handlers": [handler],
                "level": log_level,
                "propagate": False,
            },
        },
    }

    return logging_config


def setup_logging(settings: Settings) -> None:
    logging_config = get_logging_config(settings)
    logging.config.dictConfig(logging_config)
