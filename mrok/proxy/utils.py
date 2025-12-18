from collections.abc import Mapping

from mrok.proxy.constants import (
    BINARY_CONTENT_TYPES,
    BINARY_PREFIXES,
    MAX_REQUEST_BODY_BYTES,
    MAX_RESPONSE_BODY_BYTES,
    TEXTUAL_CONTENT_TYPES,
    TEXTUAL_PREFIXES,
)


def is_binary(content_type: str) -> bool:
    ct = content_type.lower()
    if ct in BINARY_CONTENT_TYPES:
        return True
    if any(ct.startswith(p) for p in BINARY_PREFIXES):
        return True
    return False


def is_textual(content_type: str) -> bool:
    ct = content_type.lower()
    if ct in TEXTUAL_CONTENT_TYPES:
        return True
    if any(ct.startswith(p) for p in TEXTUAL_PREFIXES):
        return True
    return False


def must_capture_request(
    method: str,
    headers: Mapping,
) -> bool:
    method = method.upper()

    # No body expected
    if method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return False

    content_type = headers.get("content-type", "").lower()

    content_length = None
    if "content-length" in headers:
        content_length = int(headers["content-length"])

    if is_binary(content_type):
        return False

    if content_type.startswith("multipart/form-data"):
        return False

    if content_length is not None and content_length > MAX_REQUEST_BODY_BYTES:
        return False

    if is_textual(content_type):
        return True

    if content_length is None:
        return True

    return content_length <= MAX_REQUEST_BODY_BYTES


def must_capture_response(
    headers: Mapping,
) -> bool:
    content_type = headers.get("content-type", "").lower()
    disposition = headers.get("content-disposition", "").lower()

    content_length = None
    if "content-length" in headers:
        content_length = int(headers["content-length"])

    if "attachment" in disposition:
        return False

    if is_binary(content_type):
        return False

    if content_length is not None and content_length > MAX_RESPONSE_BODY_BYTES:
        return False

    if is_textual(content_type):
        return True

    if content_length is None:
        return True

    return content_length <= MAX_RESPONSE_BODY_BYTES
