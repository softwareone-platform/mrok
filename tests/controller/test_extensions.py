from urllib.parse import quote

import pytest
from dynaconf.base import LazySettings
from httpx import AsyncClient
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture

from mrok.ziti.api import ZitiClientAPI, ZitiManagementAPI
from mrok.ziti.constants import MROK_SERVICE_TAG_NAME, MROK_VERSION_TAG_NAME
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
        "mrok.controller.routes.extensions.register_service",
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
        "mrok.controller.routes.extensions.register_service",
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
        "mrok.controller.routes.extensions.register_service",
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
        "mrok.controller.routes.extensions.unregister_service",
    )

    response = await api_client.delete("/extensions/EXT-1234-5678")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_extension_not_found(
    mocker: MockerFixture,
    api_client: AsyncClient,
):
    mocker.patch(
        "mrok.controller.routes.extensions.unregister_service",
        side_effect=ServiceNotFoundError("not found"),
    )

    response = await api_client.delete("/extensions/EXT-1234-5678")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_instances(
    mocker: MockerFixture,
    api_client: AsyncClient,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    mocker.patch(
        "mrok.controller.routes.extensions.fetch_extension_or_404",
        return_value={"name": "ext-1234-5678"},
    )
    query = quote(f'tags.{MROK_SERVICE_TAG_NAME} = "ext-1234-5678"')
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/identities?filter={query}&limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 10, "limit": 5, "offset": 0}},
            "data": [{"id": f"ins{i}", "name": "ins.svc"} for i in range(5)],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/identities?filter={query}&limit=5&offset=5",
        json={
            "meta": {"pagination": {"totalCount": 10, "limit": 5, "offset": 5}},
            "data": [{"id": f"ins{5 + i}", "name": "ins.svc"} for i in range(5)],
        },
    )
    response = await api_client.get("/extensions/ext-1234-5678/instances?limit=5&offset=0")
    assert response.status_code == 200
    page_1 = response.json()
    assert len(page_1["data"]) == 5
    assert page_1["$meta"]["pagination"]["offset"] == 0

    response = await api_client.get("/extensions/ext-1234-5678/instances?limit=5&offset=5")
    assert response.status_code == 200
    page_2 = response.json()
    assert len(page_2["data"]) == 5
    assert page_2["$meta"]["pagination"]["offset"] == 5

    assert sorted(page_1["data"], key=lambda x: x["id"]) != sorted(
        page_2["data"], key=lambda x: x["id"]
    )


@pytest.mark.asyncio
async def test_register_instance(mocker: MockerFixture, api_client: AsyncClient):
    mocker.patch(
        "mrok.controller.routes.extensions.fetch_extension_or_404",
        return_value={"name": "ext-1234-5678"},
    )
    mocked_register = mocker.patch(
        "mrok.controller.routes.extensions.register_identity",
        return_value=(
            {
                "id": "a1b2cd",
                "name": "ins-1234-5678-0001.ext-1234-5678",
                "tags": {
                    MROK_VERSION_TAG_NAME: "0.0.0.dev0",
                    MROK_SERVICE_TAG_NAME: "ext-1234-5678",
                    "account": "ACC-1234-5678",
                },
            },
            {
                "identity": "json",
            },
        ),
    )

    response = await api_client.post(
        "/extensions/ext-1234-5678/instances",
        json={
            "instance": {"id": "INS-1234-5678-0001"},
            "tags": {"account": "ACC-1234-5678"},
        },
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": "a1b2cd",
        "extension": {"id": "EXT-1234-5678"},
        "instance": {"id": "INS-1234-5678-0001"},
        "name": "ins-1234-5678-0001.ext-1234-5678",
        "status": "offline",
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            MROK_SERVICE_TAG_NAME: "ext-1234-5678",
            "account": "ACC-1234-5678",
        },
        "identity": {"identity": "json"},
    }
    assert mocked_register.call_count == 1
    assert isinstance(mocked_register.mock_calls[0].args[0], LazySettings)
    assert isinstance(mocked_register.mock_calls[0].args[1], ZitiManagementAPI)
    assert isinstance(mocked_register.mock_calls[0].args[2], ZitiClientAPI)
    assert mocked_register.mock_calls[0].args[3] == "ext-1234-5678"
    assert mocked_register.mock_calls[0].args[4] == "INS-1234-5678-0001"
    assert mocked_register.mock_calls[0].args[5] == {"account": "ACC-1234-5678"}


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["online", "offline"])
async def test_get_instance(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
    status: str,
):
    mocker.patch(
        "mrok.controller.routes.extensions.fetch_extension_or_404",
        return_value={"name": "ext-1234-5678"},
    )
    settings = settings_factory()
    query = quote(
        '(id="INS-1234-5678-0001.ext-1234-5678" or name="ins-1234-5678-0001.ext-1234-5678") '
        f"and tags.{MROK_VERSION_TAG_NAME} != null"
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/identities?filter={query}",
        json={
            "meta": {"pagination": {"totalCount": 1}},
            "data": [
                {
                    "id": "ins1",
                    "name": "ins-1234-5678-0001.ext-1234-5678",
                    "tags": {
                        MROK_VERSION_TAG_NAME: "0.0.0.dev0",
                        MROK_SERVICE_TAG_NAME: "ext-1234-5678",
                    },
                    "hasEdgeRouterConnection": status == "online",
                }
            ],
        },
    )

    response = await api_client.get("/extensions/EXT-1234-5678/instances/INS-1234-5678-0001")
    assert response.status_code == 200
    assert response.json() == {
        "id": "ins1",
        "extension": {"id": "EXT-1234-5678"},
        "instance": {"id": "INS-1234-5678-0001"},
        "name": "ins-1234-5678-0001.ext-1234-5678",
        "status": status,
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            MROK_SERVICE_TAG_NAME: "ext-1234-5678",
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["online", "offline"])
async def test_get_instance_by_instance_id(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
    status: str,
):
    mocker.patch(
        "mrok.controller.routes.extensions.fetch_extension_or_404",
        return_value={"name": "ext-1234-5678"},
    )
    settings = settings_factory()
    query = quote(f'(id="ins1" or name="ins1") and tags.{MROK_VERSION_TAG_NAME} != null')
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/identities?filter={query}",
        json={
            "meta": {"pagination": {"totalCount": 1}},
            "data": [
                {
                    "id": "ins1",
                    "name": "ins-1234-5678-0001.ext-1234-5678",
                    "hasEdgeRouterConnection": status == "online",
                    "tags": {
                        MROK_VERSION_TAG_NAME: "0.0.0.dev0",
                        MROK_SERVICE_TAG_NAME: "ext-1234-5678",
                    },
                }
            ],
        },
    )

    response = await api_client.get("/extensions/EXT-1234-5678/instances/ins1")
    assert response.status_code == 200
    assert response.json() == {
        "id": "ins1",
        "extension": {"id": "EXT-1234-5678"},
        "instance": {"id": "INS-1234-5678-0001"},
        "name": "ins-1234-5678-0001.ext-1234-5678",
        "status": status,
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            MROK_SERVICE_TAG_NAME: "ext-1234-5678",
        },
    }


@pytest.mark.asyncio
async def test_get_instance_not_found(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
):
    mocker.patch(
        "mrok.controller.routes.extensions.fetch_extension_or_404",
        return_value={"name": "ext-1234-5678"},
    )
    settings = settings_factory()
    query = quote(
        '(id="INS-1234-5678-0001.ext-1234-5678" or name="ins-1234-5678-0001.ext-1234-5678") '
        f"and tags.{MROK_VERSION_TAG_NAME} != null"
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/identities?filter={query}",
        json={
            "meta": {"pagination": {"totalCount": 10}},
            "data": [],
        },
    )

    response = await api_client.get("/extensions/EXT-1234-5678/instances/INS-1234-5678-0001")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_instance(
    mocker: MockerFixture,
    api_client: AsyncClient,
):
    mocker.patch(
        "mrok.controller.routes.extensions.fetch_instance_or_404",
        return_value={"name": "ins-1234-5678.ext-1234-5678"},
    )
    mocker.patch(
        "mrok.controller.routes.extensions.unregister_identity",
    )

    response = await api_client.delete("/extensions/EXT-1234-5678/instances/INS-1234-5678-0001")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_instance_extension_not_found(
    mocker: MockerFixture,
    api_client: AsyncClient,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    mocker.patch(
        "mrok.controller.routes.extensions.fetch_extension_or_404",
        return_value={"name": "ext-1234-5678"},
    )

    query = quote(
        '(id="INS-1234-5678-0001.ext-1234-5678" or name="ins-1234-5678-0001.ext-1234-5678") '
        f"and tags.{MROK_VERSION_TAG_NAME} != null"
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/identities?filter={query}",
        json={
            "meta": {"pagination": {"totalCount": 0}},
            "data": [],
        },
    )

    response = await api_client.delete("/extensions/EXT-1234-5678/instances/INS-1234-5678-0001")
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_instance"),
    [("online", "ins1.svc"), ("offline", "ins2.svc")],
)
async def test_get_extension_with_instances(
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
    status: str,
    expected_instance: str,
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

    query = quote(f'tags.{MROK_SERVICE_TAG_NAME} = "ext-1234-5678"')
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/identities?filter={query}&limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 2, "limit": 5, "offset": 0}},
            "data": [
                {"id": "ins1", "name": "ins1.svc", "hasEdgeRouterConnection": True},
                {"id": "ins2", "name": "ins2.svc", "hasEdgeRouterConnection": False},
            ],
        },
    )

    response = await api_client.get(f"/extensions/EXT-1234-5678?with_instances={status}")
    assert response.status_code == 200
    ext = response.json()
    assert len(ext["instances"]) == 1
    assert ext["instances"][0]["name"] == expected_instance
