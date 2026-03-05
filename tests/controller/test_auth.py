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
        assert response.headers.get("content-type") == "application/json"
        data = response.json()
        assert "detail" in data
        assert "Unauthorized" in data["detail"]


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
        assert response.headers.get("content-type") == "application/json"
        data = response.json()
        assert "detail" in data
        assert "Unauthorized" in data["detail"]


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
        url=settings.controller.auth.oidc.config_url,
        status_code=404,
    )
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        response = await client.get("/extensions", headers={"Authorization": f"Bearer {jwt_token}"})
        assert response.status_code == 401
        assert response.headers.get("content-type") == "application/json"
        data = response.json()
        assert "detail" in data
        assert "Unauthorized" in data["detail"]


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
        url=settings.controller.auth.oidc.config_url,
        json={},
    )
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        response = await client.get("/extensions", headers={"Authorization": f"Bearer {jwt_token}"})
        assert response.status_code == 401
        assert response.headers.get("content-type") == "application/json"
        data = response.json()
        assert "detail" in data
        assert "Unauthorized" in data["detail"]


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
        url=settings.controller.auth.oidc.config_url,
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
        assert response.headers.get("content-type") == "application/json"
        data = response.json()
        assert "detail" in data
        assert "Unauthorized" in data["detail"]


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
        url=settings.controller.auth.oidc.config_url,
        json=openid_config,
    )
    httpx_mock.add_response(method="GET", url=openid_config["jwks_uri"], status_code=200, json={})
    async with AsyncClient(
        transport=ASGITransport(app=app_lifespan_manager.app),
        base_url=f"http://localhost/{fastapi_app.root_path.removeprefix('/')}/",
    ) as client:
        response = await client.get("/extensions", headers={"Authorization": f"Bearer {jwt_token}"})
        assert response.status_code == 401
        assert response.headers.get("content-type") == "application/json"
        data = response.json()
        assert "detail" in data
        assert "Unauthorized" in data["detail"]


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
        url=settings.controller.auth.oidc.config_url,
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
        assert response.headers.get("content-type") == "application/json"
        data = response.json()
        assert "detail" in data
        assert "Unauthorized" in data["detail"]


@pytest.mark.parametrize("exc_type", [jwt.InvalidTokenError, jwt.InvalidKeyError])
async def test_invalid_key_or_token_error(
    api_client: AsyncClient,
    mocker: MockerFixture,
    exc_type: type[Exception],
):
    mocker.patch("mrok.authentication.backends.oidc.jwt.decode", side_effect=exc_type("bla"))
    response = await api_client.get("/extensions")
    assert response.status_code == 401
    assert response.headers.get("content-type") == "application/json"
    data = response.json()
    assert "detail" in data
    assert "Unauthorized" in data["detail"]


# ---- JWT backend -----


@pytest.mark.asyncio
async def test_valid_token_with_oidc(
    api_client: AsyncClient,
    mock_empty_services,
):
    resp = await api_client.get("/extensions")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_oidc_fails_jwt_succeeds(
    api_client_dual_backend: AsyncClient,
    mock_empty_services,
    mocker: MockerFixture,
):
    mocker.patch(
        "mrok.authentication.backends.oidc.OIDCJWTAuthenticationBackend.authenticate",
        new=mocker.AsyncMock(return_value=None),
    )

    resp = await api_client_dual_backend.get("/extensions")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_all_backends_fail(
    api_client_dual_backend: AsyncClient,
    mock_empty_services,
    mocker: MockerFixture,
):
    mocker.patch(
        "mrok.authentication.backends.oidc.OIDCJWTAuthenticationBackend.authenticate",
        new=mocker.AsyncMock(return_value=None),
    )

    mocker.patch(
        "mrok.authentication.backends.jwt.JWTAuthenticationBackend.authenticate",
        new=mocker.AsyncMock(return_value=None),
    )

    response = await api_client_dual_backend.get("/extensions")

    assert response.status_code == 401
    assert response.headers.get("content-type") == "application/json"
    data = response.json()
    assert "detail" in data
    assert "Unauthorized" in data["detail"]


@pytest.mark.parametrize(
    "exc",
    [jwt.InvalidTokenError, jwt.InvalidKeyError],
)
@pytest.mark.asyncio
async def test_jwt_backend_exceptions(
    api_client_dual_backend: AsyncClient,
    mock_empty_services,
    mocker: MockerFixture,
    exc,
):
    mocker.patch(
        "mrok.authentication.backends.oidc.OIDCJWTAuthenticationBackend.authenticate",
        new=mocker.AsyncMock(return_value=None),
    )

    mocker.patch(
        "mrok.authentication.backends.jwt.jwt.decode",
        side_effect=exc("boom"),
    )

    response = await api_client_dual_backend.get("/extensions")

    assert response.status_code == 401
    assert response.headers.get("content-type") == "application/json"
    data = response.json()
    assert "detail" in data
    assert "Unauthorized" in data["detail"]
