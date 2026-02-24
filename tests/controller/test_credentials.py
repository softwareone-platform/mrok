import pytest

from mrok.authentication import credentials


def test_bearer_with_empty_string():
    scope = {
        "type": "http",
        "headers": [(b"authorization", b"Bearer ")],
    }
    assert credentials.BearerCredentials.extract_from_asgi_scope(scope) is None


def test_missing_token():
    scope = {
        "type": "http",
        "headers": [],
    }
    assert credentials.BearerCredentials.extract_from_asgi_scope(scope) is None


def test_valid_bearer_returns_credentials():
    scope = {
        "type": "http",
        "headers": [(b"authorization", b"Bearer token")],
    }
    creds = credentials.BearerCredentials.extract_from_asgi_scope(scope)

    assert isinstance(creds, credentials.BearerCredentials)
    assert creds.credentials == "token"


@pytest.mark.parametrize(
    "header",
    [
        "BEARER token",
        "BeaRer token",
        "bearer token",
        "Bearer token",
    ],
)
def test_case_insensitive_bearer_token(header):
    scope = {
        "type": "http",
        "headers": [(b"authorization", header.encode("latin-1"))],
    }
    creds = credentials.BearerCredentials.extract_from_asgi_scope(scope)
    assert isinstance(creds, credentials.BearerCredentials)
    assert creds.credentials == "token"


def test_extra_spaced_bearer_token():
    scope = {
        "type": "http",
        "headers": [(b"authorization", b"Bearer        token")],
    }
    creds = credentials.BearerCredentials.extract_from_asgi_scope(scope)
    assert isinstance(creds, credentials.BearerCredentials)
    assert creds.credentials == "token"
