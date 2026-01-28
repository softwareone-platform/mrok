import multiprocessing
import re

import typer

from mrok.conf import get_settings


def number_of_workers() -> int:
    return (multiprocessing.cpu_count() * 2) + 1


def validate_identifier(regex_exp: str, format: str, identifier: str) -> str:
    match = re.fullmatch(regex_exp, identifier)
    if not match:
        raise typer.BadParameter(f"it must match {format}")
    return identifier


def validate_extension_id(extension_id: str) -> str:
    settings = get_settings()
    return validate_identifier(
        settings.identifiers.extension.regex, settings.identifiers.extension.format, extension_id
    )


def validate_instance_id(instance_id: str) -> str:
    settings = get_settings()
    return validate_identifier(
        settings.identifiers.instance.regex, settings.identifiers.instance.format, instance_id
    )
