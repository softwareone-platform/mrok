from collections.abc import Generator
from dataclasses import dataclass
from io import BytesIO

from multipart import MultipartParser

TEXTUAL_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-www-form-urlencoded",
}

TEXTUAL_PREFIXES = ("text/",)

CONTENT_TYPE_TO_LANGUAGE = {
    "application/json": "json",
    "application/ld+json": "json",
    "application/problem+json": "json",
    "application/schema+json": "json",
    "application/xml": "xml",
    "text/xml": "xml",
    "application/xhtml+xml": "html",
    "text/html": "html",
    "text/css": "css",
    "application/javascript": "javascript",
    "application/x-javascript": "javascript",
    "text/javascript": "javascript",
    "application/ecmascript": "javascript",
    "text/markdown": "markdown",
    "text/x-markdown": "markdown",
    "application/yaml": "yaml",
    "application/x-yaml": "yaml",
    "text/yaml": "yaml",
    "application/toml": "toml",
    "application/x-toml": "toml",
    "application/sql": "sql",
    "text/x-sql": "sql",
    "application/java": "java",
    "text/x-java-source": "java",
    "application/python": "python",
    "text/x-python": "python",
    "application/x-python-code": "python",
    "application/rust": "rust",
    "text/x-rust": "rust",
    "application/go": "go",
    "text/x-go": "go",
    "application/bash": "bash",
    "application/x-sh": "bash",
    "text/x-shellscript": "bash",
    "application/regex": "regex",
    "text/x-regex": "regex",
}


@dataclass
class ContentTypeInfo:
    content_type: str
    binary: bool
    charset: str | None = None
    boundary: str | None = None


def parse_content_type(content_type_header: str) -> ContentTypeInfo:
    parts = content_type_header.split(";")
    content_type = parts[0].strip().lower()

    charset = None
    boundary = None

    for part in parts[1:]:
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            key = key.strip().lower()
            value = value.strip().strip('"')
            if key == "charset":
                charset = value
            elif key == "boundary":
                boundary = value

    binary = not is_textual(content_type)

    if charset is None and not binary:
        charset = "utf-8"

    return ContentTypeInfo(
        content_type=content_type, binary=binary, charset=charset, boundary=boundary
    )


def parse_form_data(data: bytes, boundary: str) -> Generator[tuple[str, str]]:
    parser = MultipartParser(BytesIO(data), boundary)
    for part in parser:
        if is_textual(part.content_type):
            yield part.name, part.value
            continue
        yield part.name, "<binary>"


def is_textual(content_type: str) -> bool:
    ct = content_type.lower()
    if ct in TEXTUAL_CONTENT_TYPES:
        return True
    if any(ct.startswith(p) for p in TEXTUAL_PREFIXES):
        return True
    return False


def build_tree(node, data):
    if isinstance(data, dict):
        for key, value in data.items():
            child = node.add(str(key))
            build_tree(child, value)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            child = node.add(f"[{index}]")
            build_tree(child, value)
    else:
        node.add(repr(data))


def hexdump(data, width=16):
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{hex_part:<{width * 3}} {ascii_part}")
    return "\n".join(lines)


def humanize_bytes(num_bytes: int) -> tuple[float, str]:  # type: ignore[return-value]
    if num_bytes < 0:
        raise ValueError("num_bytes must be non-negative")

    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    value = float(num_bytes)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return round(value, 2), unit
        value /= 1024


def get_highlighter_language_by_content_type(content_type: str) -> str | None:
    if content_type in CONTENT_TYPE_TO_LANGUAGE:
        return CONTENT_TYPE_TO_LANGUAGE[content_type]
    return None
