import jwt
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture

from tests.conftest import SettingsFactory


@pytest.mark.asyncio
async def test_no_token(
    fastapi_app: FastAPI,
    app_lifespan_manager: LifespanManager,
):
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        response = await client.get("/extensions")
        assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("auth_header", ["Bearer invalid", "invalid", ""])
async def test_invalid_token(
    fastapi_app: FastAPI,
    app_lifespan_manager: LifespanManager,
    auth_header: str,
):
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
        headers={"Authorization": auth_header},
    ) as client:
        response = await client.get("/extensions")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_openid_config_url(
    fastapi_app: FastAPI,
    app_lifespan_manager: LifespanManager,
    httpx_mock: HTTPXMock,
    settings_factory: SettingsFactory,
    jwt_token: str,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=settings.auth.openid_config_url,
        status_code=404,
    )
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        response = await client.get("/extensions", headers={"Authorization": f"Bearer {jwt_token}"})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_openid_config_data(
    fastapi_app: FastAPI,
    app_lifespan_manager: LifespanManager,
    httpx_mock: HTTPXMock,
    settings_factory: SettingsFactory,
    jwt_token: str,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=settings.auth.openid_config_url,
        json={},
    )
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        response = await client.get("/extensions", headers={"Authorization": f"Bearer {jwt_token}"})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_jwks_url(
    fastapi_app: FastAPI,
    app_lifespan_manager: LifespanManager,
    httpx_mock: HTTPXMock,
    settings_factory: SettingsFactory,
    jwt_token: str,
    openid_config: dict,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=settings.auth.openid_config_url,
        json=openid_config,
    )
    httpx_mock.add_response(
        method="GET",
        url=openid_config["jwks_uri"],
        status_code=404,
    )
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        response = await client.get("/extensions", headers={"Authorization": f"Bearer {jwt_token}"})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_jwks_data(
    fastapi_app: FastAPI,
    app_lifespan_manager: LifespanManager,
    httpx_mock: HTTPXMock,
    settings_factory: SettingsFactory,
    jwt_token: str,
    openid_config: dict,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=settings.auth.openid_config_url,
        json=openid_config,
    )
    httpx_mock.add_response(method="GET", url=openid_config["jwks_uri"], status_code=200, json={})
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        response = await client.get("/extensions", headers={"Authorization": f"Bearer {jwt_token}"})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_jwks_key_not_found(
    fastapi_app: FastAPI,
    app_lifespan_manager: LifespanManager,
    httpx_mock: HTTPXMock,
    settings_factory: SettingsFactory,
    jwt_token: str,
    openid_config: dict,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=settings.auth.openid_config_url,
        json=openid_config,
    )
    httpx_mock.add_response(
        method="GET", url=openid_config["jwks_uri"], status_code=200, json={"keys": []}
    )
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        response = await client.get("/extensions", headers={"Authorization": f"Bearer {jwt_token}"})
        assert response.status_code == 401


@pytest.mark.parametrize("exc_type", [jwt.InvalidTokenError, jwt.InvalidKeyError])
async def test_invalid_key_or_token_error(
    api_client: AsyncClient,
    mocker: MockerFixture,
    exc_type: type[Exception],
):
    mocker.patch("mrok.controller.auth.jwt.decode", side_effect=exc_type("bla"))
    resp = await api_client.get("/extensions")
    assert resp.status_code == 401
