import typer

from mrok.ziti.api import TagsType


def parse_tags(pairs: list[str] | None) -> TagsType | None:
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
