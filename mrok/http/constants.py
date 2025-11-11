MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BODY_BYTES = 5 * 1024 * 1024

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
