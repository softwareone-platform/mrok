from urllib.parse import quote

import pytest
from dynaconf.base import LazySettings
from httpx import AsyncClient
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture

from mrok.ziti.api import ZitiManagementAPI
from mrok.ziti.constants import MROK_VERSION_TAG_NAME
from mrok.ziti.errors import (
    ConfigTypeNotFoundError,
    MrokError,
    ProxyIdentityNotFoundError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
)
from tests.conftest import SettingsFactory


@pytest.mark.asyncio
async def test_list_extensions(
    api_client: AsyncClient, settings_factory: SettingsFactory, httpx_mock: HTTPXMock
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services?limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 10, "limit": 5, "offset": 0}},
            "data": [{"id": f"svc{i}", "name": "svc"} for i in range(5)],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services?limit=5&offset=5",
        json={
            "meta": {"pagination": {"totalCount": 10, "limit": 5, "offset": 5}},
            "data": [{"id": f"svc{5 + i}", "name": "svc"} for i in range(5)],
        },
    )
    response = await api_client.get("/extensions?limit=5&offset=0")
    assert response.status_code == 200
    page_1 = response.json()
    assert len(page_1["data"]) == 5
    assert page_1["$meta"]["pagination"]["offset"] == 0

    response = await api_client.get("/extensions?limit=5&offset=5")
    assert response.status_code == 200
    page_2 = response.json()
    assert len(page_2["data"]) == 5
    assert page_2["$meta"]["pagination"]["offset"] == 5

    assert sorted(page_1["data"], key=lambda x: x["id"]) != sorted(
        page_2["data"], key=lambda x: x["id"]
    )


@pytest.mark.asyncio
async def test_register_extension(mocker: MockerFixture, api_client: AsyncClient):
    mocked_register = mocker.patch(
        "mrok.controller.routes.register_extension",
        return_value={
            "id": "a1b2cd",
            "name": "ext-1234-5678",
            "tags": {
                MROK_VERSION_TAG_NAME: "0.0.0.dev0",
                "account": "ACC-1234-5678",
            },
        },
    )

    response = await api_client.post(
        "/extensions",
        json={
            "extension": {"id": "EXT-1234-5678"},
            "tags": {"account": "ACC-1234-5678"},
        },
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": "a1b2cd",
        "extension": {"id": "EXT-1234-5678"},
        "name": "ext-1234-5678",
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            "account": "ACC-1234-5678",
        },
    }
    assert mocked_register.call_count == 1
    assert isinstance(mocked_register.mock_calls[0].args[0], LazySettings)
    assert isinstance(mocked_register.mock_calls[0].args[1], ZitiManagementAPI)
    assert mocked_register.mock_calls[0].args[2] == "EXT-1234-5678"
    assert mocked_register.mock_calls[0].args[3] == {"account": "ACC-1234-5678"}


@pytest.mark.asyncio
async def test_register_extension_already_exists(mocker: MockerFixture, api_client: AsyncClient):
    mocker.patch(
        "mrok.controller.routes.register_extension",
        side_effect=ServiceAlreadyRegisteredError("Extension `EXT-1234-5678` already registered."),
    )

    response = await api_client.post(
        "/extensions",
        json={
            "extension": {"id": "EXT-1234-5678"},
            "tags": {"account": "ACC-1234-5678"},
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Extension `EXT-1234-5678` already registered."}


@pytest.mark.asyncio
@pytest.mark.parametrize("exc_type", [ProxyIdentityNotFoundError, ConfigTypeNotFoundError])
async def test_register_extension_mrok_not_configured(
    mocker: MockerFixture,
    api_client: AsyncClient,
    exc_type: MrokError,
):
    mocker.patch(
        "mrok.controller.routes.register_extension",
        side_effect=exc_type("this is the error."),  # type: ignore
    )

    response = await api_client.post(
        "/extensions",
        json={
            "extension": {"id": "EXT-1234-5678"},
            "tags": {"account": "ACC-1234-5678"},
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "OpenZiti not configured properly: this is the error."}


@pytest.mark.asyncio
async def test_get_extension(
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    query = quote(
        f'(id="EXT-1234-5678" or name="ext-1234-5678") and tags.{MROK_VERSION_TAG_NAME} != null'
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services?filter={query}",
        json={
            "meta": {"pagination": {"totalCount": 1}},
            "data": [
                {
                    "id": "svc1",
                    "name": "ext-1234-5678",
                    "tags": {MROK_VERSION_TAG_NAME: "0.0.0.dev0"},
                }
            ],
        },
    )

    response = await api_client.get("/extensions/EXT-1234-5678")
    assert response.status_code == 200
    assert response.json() == {
        "id": "svc1",
        "extension": {"id": "EXT-1234-5678"},
        "name": "ext-1234-5678",
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
        },
    }


@pytest.mark.asyncio
async def test_get_extension_not_found(
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    query = quote(
        f'(id="EXT-1234-5678" or name="ext-1234-5678") and tags.{MROK_VERSION_TAG_NAME} != null'
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services?filter={query}",
        json={
            "meta": {"pagination": {"totalCount": 0}},
            "data": [],
        },
    )

    response = await api_client.get("/extensions/EXT-1234-5678")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_extension(
    mocker: MockerFixture,
    api_client: AsyncClient,
):
    mocker.patch(
        "mrok.controller.routes.unregister_extension",
    )

    response = await api_client.delete("/extensions/EXT-1234-5678")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_extension_not_found(
    mocker: MockerFixture,
    api_client: AsyncClient,
):
    mocker.patch(
        "mrok.controller.routes.unregister_extension", side_effect=ServiceNotFoundError("not found")
    )

    response = await api_client.delete("/extensions/EXT-1234-5678")
    assert response.status_code == 404
