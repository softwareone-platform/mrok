import asyncio
import json
import tempfile
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from asgi_lifespan import LifespanManager
from dynaconf import Dynaconf
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest_httpx import HTTPXMock

from mrok.conf import Settings, get_settings
from mrok.types.proxy import ASGIReceive, ASGISend, Message
from tests.types import ReceiveFactory, SendFactory, SettingsFactory


@pytest.fixture(scope="session")
def settings_factory() -> SettingsFactory:
    def _get_settings(
        ziti: dict | None = None,
        logging: dict | None = None,
        pagination: dict | None = None,
        proxy: dict | None = None,
        auth: dict | None = None,
        sidecar: dict | None = None,
    ) -> Settings:
        ziti = ziti or {
            "api": {
                "management": "https://ziti.example.com",
                "client": "https://ziti.example.com",
            },
            "read_timeout": 10,
            "ssl_verify": True,
            "auth": {"username": "user", "password": "pass", "identity": None},
        }
        logging = logging or {
            "debug": True,
            "rich": False,
        }
        pagination = pagination or {"limit": 5}
        auth = auth or {
            "openid_config_url": "http://example.com/openid-configuration",
            "audience": "mrok-audience",
            "read_timeout": 10,
        }
        proxy = proxy or {
            "identity": "public",
            "mode": "zrok",
            "domain": "exts.s1.today",
        }
        sidecar = sidecar or {
            "textual_port": 4040,
            "store_port": 5051,
            "store_size": 1000,
            "textual_command": "python mrok/agent/sidecar/inspector.py",
        }
        settings = Dynaconf(
            environments=True,
            settings_files=[],
            ENV_FOR_DYNACONF="testing",
            ZITI=ziti,
            LOGGING=logging,
            PAGINATION=pagination,
            PROXY=proxy,
            AUTH=auth,
            SIDECAR=sidecar,
        )

        return settings

    return _get_settings


@pytest.fixture()
def ziti_bad_request_error() -> dict[str, Any]:
    return {
        "error": {
            "code": "error_code",
            "message": "error_message",
            "cause": {
                "field": "field_name",
                "reason": "field_error",
            },
        }
    }


@pytest.fixture()
def ziti_identity_json() -> dict[str, Any]:
    return {
        "ztAPI": "https://ziti.platform.softwareone.com/edge/client/v1",
        "ztAPIs": None,
        "configTypes": None,
        "id": {
            "key": "pem:-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
            "cert": "pem:-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
            "ca": "pem:-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
        },
        "enableHa": False,
        "mrok": {
            "identity": "ins-0000-0000-0000.ext-0000-0000",
            "extension": "ext-0000-0000",
            "instance": "ins-0000-0000-0000",
            "domain": "exts.platform.softwareone.com",
            "tags": {
                "mrok-service": "ext-0000-0000",
                "mrok-identity-type": "instance",
                "mrok": "0.4.0",
            },
        },
    }


@pytest.fixture()
def ziti_identity_file(ziti_identity_json: dict[str, Any]) -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile("w", suffix="json") as f:
        json.dump(ziti_identity_json, f)
        f.seek(0)
        yield f.name


@pytest.fixture()
def jwt_signing_key() -> str:
    return """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDh0IIuMVuxXSq1
ndmO13RLpqv+3Ndyh0aEP8Lz3/zQeyliYCfW8HMoP8vjC9ftGKdEHLG4eoUs6NF+
8dYh3MRtDikl0oH/J+/6DFS3zqG+NNaMUpTgmKsrn1w5MN/NPQxPp/Djc4nAcAoi
V/c0w5fft5CLoLkLt5iL8y2mTuR0VRhZ6fS+hQiQMcSBajtr8jPLhem9spJ53N5x
X/OQNTkP712s9qSwCLd8SoFzNFYam2kHKs+nfMbXmk0PXbLjTb9Sk6pOa4Ey5OZU
//8oFyMnEltuRUH158WskpxSsxwZosPOsrFXcEdq5DHPQppc5H6IjwevVr8VZCZ9
y0DhqbpHAgMBAAECggEAa23BiQ1VVIeA2p9qkbDBtH3qJJlW7DccHq2g51nf0iVN
1m3tdi21c2gKbQ1E4BjS9q36BMxREEEA7bZKy5hWYJWUkNhZnRSYb+qu4TUuMKm9
ikt9ZW5sPJgXjWPJjUAmW70HdoYQelszDwyvYExPNBEF9M91SXRCYA5EYPL2b7rp
FjUzbq4/a4C9GYUP7EhBYYyZ+KnFDa9mxdbUFrQgupV2b+v2sPeOmkDRhzjAp7HC
yRcUnTmQM32LMO57oFZ7K9DJDMwxbHCAE7N8f2Uge2VLpIUjz3GskdjPcLBqu4qH
938dL3GMvKglo18VRSKiTkwxjxnP8HA8+0ifRv7cIQKBgQD7irdN/lYXdlhKAXwt
eQ5Tua3/Zi3Xia0dgOEzGxfVT1L6rVjVa149/v7x26p0evt0c9gkcHlBgUDEH7yz
sEDY/KwIo9Wg2Bpe1iUNcO/BvZc0mc3Cu9D8agxNZ5eHq+a36gTKR/QD1dp+48zK
6yimXxEfUYy2u8TBLm2Jk3hx4QKBgQDl0RA+L/SP8d2lB4vPDSSFhMYnwaH4njbq
/S8evNFcyKba9HaA8Sbng/msI/k8rnyul5GqFVooVl9TfPa93ATvagzijBvvqZ6R
j2+41hEAxmZ2257DKYpQ4JM2mRl9pOFQrc1GRbUfSOJAekj2O/2ojnbHHUcxg0dS
yliskq6BJwKBgGxVDKcBb5CBPnr48sMezMXQRRimp/2Y5L69H8AD3hrXI/SkLYsU
x6zJooEFSv8JbDx2G9NtwTst8HfG910n/nW1NF4wOTQhfhH0BlcomYmGHpXf25cP
jmz3Oz8m60LaDO6OUevQW04/ju9xKmUGLCai8NvdIk4cxhsw5KoIoinhAoGBALDu
vCqkkQ0hkRs1LBZEcBG7nzOMiD740B8qvdRUWnusn4mDHJk5EFK98MLvDzwAuk1Q
s/zWY4satFl6pByX/9SzOShR5lAlrscyPzl21bBbDxgDDcADg1GxFKW8STvKbQ3I
QXoQwNlNK6OogfPRTAExbZDuoZklEQxUbOCwLVmRAoGACIi7DWWZr9Ea4ag82yYv
CBdlKSshb2RYGdbYm9dzeqqv1/xtwtFYMOuLilL3qp9erBAsc6Kdz+n3v1+2p7Ho
3/upcFI5QbhGHCO5J92fdDYh6rsAG4cwC5LlAC5WgP3bL9+QVKKcYm8/mmglLIu3
XIvgj23tDAmXtVRh0MsgOH4=
-----END PRIVATE KEY-----
"""


@pytest.fixture()
def jwt_token(jwt_signing_key: str) -> str:
    payload = {
        "sub": "user123",
        "aud": "mrok-audience",
        "iss": "http:/test.mrok/",
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }
    return jwt.encode(payload, jwt_signing_key, algorithm="RS256", headers={"kid": "test-key"})


@pytest.fixture()
def jwks_json() -> dict:
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "test-key",
                "n": (
                    "4dCCLjFbsV0qtZ3Zjtd0S6ar_tzXcodGhD_C89_80HspYmAn1vBzKD_"
                    "L4wvX7RinRByxuHqFLOjRfvHWIdzEbQ4pJdKB_yfv-gxUt86hvjTWjF"
                    "KU4JirK59cOTDfzT0MT6fw43OJwHAKIlf3NMOX37eQi6C5C7eYi_Mtp"
                    "k7kdFUYWen0voUIkDHEgWo7a_Izy4XpvbKSedzecV_zkDU5D-9drPak"
                    "sAi3fEqBczRWGptpByrPp3zG15pND12y402_UpOqTmuBMuTmVP__KBc"
                    "jJxJbbkVB9efFrJKcUrMcGaLDzrKxV3BHauQxz0KaXOR-iI8Hr1a_FW"
                    "QmfctA4am6Rw"
                ),
                "e": "AQAB",
            }
        ]
    }


@pytest.fixture()
def openid_config() -> dict:
    return {"issuer": "http:/test.mrok/", "jwks_uri": "http://example.com/jwks.json"}


@pytest.fixture()
def fastapi_app(settings_factory: SettingsFactory) -> FastAPI:
    settings = settings_factory()
    from mrok.controller.app import setup_app

    app = setup_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture()
async def app_lifespan_manager(fastapi_app: FastAPI) -> AsyncGenerator[LifespanManager, None]:
    async with LifespanManager(fastapi_app) as lifespan_manager:
        yield lifespan_manager


@pytest.fixture
async def api_client(
    fastapi_app: FastAPI,
    app_lifespan_manager: LifespanManager,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
    openid_config: dict,
    jwks_json: dict,
    jwt_token: str,
) -> AsyncGenerator[AsyncClient]:
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=settings.auth.openid_config_url,
        json=openid_config,
        is_reusable=True,
    )
    httpx_mock.add_response(
        method="GET",
        url="http://example.com/jwks.json",
        json=jwks_json,
        is_reusable=True,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
        headers={"Authorization": f"Bearer {jwt_token}"},
    ) as client:
        yield client


@pytest.fixture
def receive_factory() -> ReceiveFactory:
    def _factory(messages: list[Message] | None = None) -> ASGIReceive:
        if not messages:
            messages = [{"type": "http.request", "body": b"", "more_body": False}]

        class Receiver:
            def __init__(self, messages: list[Message]):
                self.messages = messages

            async def __call__(self):
                await asyncio.sleep(0)
                try:
                    return self.messages.pop(0)
                except Exception:
                    return

        return Receiver(messages)

    return _factory


@pytest.fixture
def send_factory() -> SendFactory:
    def _factory(collected: list[Message]) -> ASGISend:
        async def send(message: Message) -> None:
            await asyncio.sleep(0)
            collected.append(message)

        return send

    return _factory
