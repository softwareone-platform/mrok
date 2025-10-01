import json
import tempfile
from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from dynaconf import Dynaconf
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mrok.conf import Settings, get_settings

SettingsFactory = Callable[..., Settings]


@pytest.fixture(scope="session")
def settings_factory() -> SettingsFactory:
    def _get_settings(
        ziti: dict | None = None,
        logging: dict | None = None,
        pagination: dict | None = None,
        proxy: dict | None = None,
    ) -> Settings:
        ziti = ziti or {
            "url": "https://ziti.example.com",
            "read_timeout": 10,
            "ssl_verify": True,
            "auth": {"username": "user", "password": "pass", "identity": None},
        }
        logging = logging or {
            "debug": True,
            "rich": False,
        }
        pagination = pagination or {"limit": 5}
        proxy = proxy or {
            "identity": "public",
            "mode": "zrok",
            "domain": "exts.s1.today",
        }
        settings = Dynaconf(
            environments=True,
            settings_files=[],
            ENV_FOR_DYNACONF="testing",
            ZITI=ziti,
            LOGGING=logging,
            PAGINATION=pagination,
            PROXY=proxy,
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
        "ztAPI": "https://ziti.exts.platform.softwareone.com/edge/client/v1",
        "ztAPIs": None,
        "configTypes": None,
        "id": {
            "key": "pem:-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
            "cert": "pem:-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
            "ca": "pem:-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
        },
        "enableHa": None,
        "mrok": {"identity": "ins-1234-5678-0001.ext-1234-5678"},
    }


@pytest.fixture()
def ziti_identity_file(ziti_identity_json: dict[str, Any]) -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile("w", suffix="json") as f:
        json.dump(ziti_identity_json, f)
        f.seek(0)
        yield f.name


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
) -> AsyncGenerator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        yield client
