import pytest

from mrok.authentication import credentials


def test_no_bearer_token():
    assert credentials.BearerCredentials.from_authorization_header(None) is None


def test_bearer_with_empty_string():
    assert credentials.BearerCredentials.from_authorization_header("") is None


def test_missing_token():
    assert credentials.BearerCredentials.from_authorization_header("Bearer ") is None


def test_valid_bearer_returns_credentials():
    creds = credentials.BearerCredentials.from_authorization_header("Bearer token")

    assert isinstance(creds, credentials.BearerCredentials)
    assert creds.token == "token"


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
    creds = credentials.BearerCredentials.from_authorization_header(header)
    assert isinstance(creds, credentials.BearerCredentials)
    assert creds.token == "token"


def test_extra_spaced_bearer_token():
    creds = credentials.BearerCredentials.from_authorization_header("BEARER          token")
    assert isinstance(creds, credentials.BearerCredentials)
    assert creds.token == "token"
