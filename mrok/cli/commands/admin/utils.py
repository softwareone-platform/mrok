from datetime import datetime

import typer

from mrok.types.ziti import Tags


def parse_tags(pairs: list[str] | None) -> Tags | None:
    if not pairs:
        return None

    result: dict[str, str | bool | None] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"Invalid format {item!r}, expected key=value")
        key, raw = item.split("=", 1)
        raw_lower = raw.strip().lower()
        if raw_lower in ("true", "false"):
            val: str | bool | None = raw_lower == "true"
        elif raw == "":
            val = None
        else:
            val = raw
        result[key.strip()] = val
    return result


def tags_to_filter(tags: list[str]) -> str:
    parsed_tags = parse_tags(tags)
    return " and ".join([f'tags.{key}="{value}"' for key, value in parsed_tags.items()])


def format_timestamp(iso_timestamp: str) -> str:
    dt = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_tags(tags: dict, delimiter: str = "\n") -> str:
    if not tags:
        return "-"

    return f"{delimiter}".join(f"{k}: {v}" for k, v in tags.items())


def extract_names(data: list[dict], delimiter: str = "\n") -> str:
    if not data:
        return "-"

    return f"{delimiter}".join(item["name"] for item in data if item.get("name"))
