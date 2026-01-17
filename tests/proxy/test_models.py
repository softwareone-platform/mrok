import base64
import secrets
from typing import Any

import pytest

from mrok.proxy.models import FixedSizeByteBuffer, HTTPHeaders, HTTPRequest, Identity


def test_identity(ziti_identity_json: dict[str, Any], ziti_identity_file: str):
    identity = Identity.load_from_file(ziti_identity_file)
    assert identity.zt_api == ziti_identity_json["ztAPI"]
    assert identity.id.key == ziti_identity_json["id"]["key"][4:]
    assert identity.id.cert == ziti_identity_json["id"]["cert"][4:]
    assert identity.id.ca == ziti_identity_json["id"]["ca"][4:]
    assert identity.mrok.extension == ziti_identity_json["mrok"]["extension"]
    assert identity.mrok.instance == ziti_identity_json["mrok"]["instance"]


def test_fixed_size_buffer():
    chunks = [secrets.token_bytes(10) for _ in range(10)]
    fsb = FixedSizeByteBuffer(100)
    for idx in range(10):
        fsb.write(chunks[idx])

    assert fsb.getvalue() == b"".join(chunks)
    assert fsb.overflow is False


def test_fixed_size_buffer_write_no_data():
    fsb = FixedSizeByteBuffer(100)
    fsb.write(b"")
    assert fsb.getvalue() == b""
    fsb.write(None)
    assert fsb.getvalue() == b""


def test_fixed_size_buffer_overflow():
    chunks = [secrets.token_bytes(7) for _ in range(15)]
    fsb = FixedSizeByteBuffer(100)
    for idx in range(15):
        fsb.write(chunks[idx])

    assert len(fsb.getvalue()) == 100
    assert fsb.overflow is True


def test_fixed_size_buffer_full():
    chunks = [secrets.token_bytes(10) for _ in range(10)]
    fsb = FixedSizeByteBuffer(100)
    for idx in range(10):
        fsb.write(chunks[idx])

    assert fsb.getvalue() == b"".join(chunks)
    assert fsb.overflow is False
    fsb.write(secrets.token_bytes(10))
    assert fsb.getvalue() == b"".join(chunks)
    assert fsb.overflow is True


def test_fixed_size_buffer_clear():
    chunks = [secrets.token_bytes(10) for _ in range(10)]
    fsb = FixedSizeByteBuffer(100)
    for idx in range(10):
        fsb.write(chunks[idx])

    assert len(fsb.getvalue()) == 100
    assert fsb.overflow is False
    fsb.write(secrets.token_bytes(10))
    assert fsb.getvalue() == b"".join(chunks)
    assert fsb.overflow is True
    fsb.clear()
    assert fsb.getvalue() == b""
    assert fsb.overflow is False


def test_http_headers():
    headers = HTTPHeaders()
    headers["content-type"] = "application/json"

    assert headers["Content-tYpe"] == "application/json"
    assert headers.get("CONTENT-TYPE", "boh") == "application/json"
    assert headers.get("Accept", "whatever") == "whatever"
    assert headers.get("Accept") is None
    del headers["Content-tYpe"]
    with pytest.raises(KeyError):
        headers["content-type"]

    headers = HTTPHeaders(
        initial={"x-initial-header": "my-value"},
    )
    assert headers["X-Initial-Header"] == "my-value"


def test_http_headers_from_asgi():
    headers = HTTPHeaders.from_asgi(
        [
            (b"content-type", b"text/html"),
            (b"aCCept", b"application/json"),
        ]
    )

    assert headers["Content-Type"] == "text/html"
    assert headers["Accept"] == "application/json"


def test_httprequest_serialization():
    headers = HTTPHeaders.from_asgi(
        [
            (b"content-type", b"text/html"),
            (b"aCCept", b"application/json"),
        ]
    )

    req = HTTPRequest(
        method="GET",
        url="/path/to/resource",
        headers=headers,
        query_string=b"foo=bar",
        start_time=2.0,
        body=b"This is the body",
        body_truncated=False,
    )

    serialized = req.model_dump()
    assert serialized == {
        "method": "GET",
        "url": "/path/to/resource",
        "headers": {"accept": "application/json", "content-type": "text/html"},
        "query_string": base64.b64encode(b"foo=bar").decode(),
        "body": base64.b64encode(
            b"This is the body",
        ).decode(),
        "start_time": 2.0,
        "body_truncated": False,
    }


def test_httprequest_deserialization():
    serialized = {
        "method": "GET",
        "url": "/path/to/resource",
        "headers": {"accept": "application/json", "content-type": "text/html"},
        "query_string": base64.b64encode(b"foo=bar").decode(),
        "body": base64.b64encode(b"This is the body").decode(),
        "start_time": 2.0,
        "body_truncated": False,
    }
    req = HTTPRequest.model_validate(serialized)

    assert req.method == "GET"
    assert req.url == "/path/to/resource"
    assert len(req.headers) == 2
    assert req.headers["accept"] == "application/json"
    assert req.headers["content-type"] == "text/html"
    assert req.query_string == b"foo=bar"
    assert req.body == b"This is the body"
    assert req.start_time == 2.0
    assert req.body_truncated is False
