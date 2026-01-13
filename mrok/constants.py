import re

RE_EXTENSION_ID = re.compile(r"(?i)EXT-\d{4}-\d{4}")
RE_INSTANCE_ID = re.compile(r"(?i)INS-\d{4}-\d{4}-\d{4}")


BINARY_CONTENT_TYPES = {
    "application/octet-stream",
    "application/pdf",
}

BINARY_PREFIXES = (
    "image/",
    "video/",
    "audio/",
)

TEXTUAL_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-www-form-urlencoded",
}

TEXTUAL_PREFIXES = ("text/",)
