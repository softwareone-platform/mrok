from urllib.parse import quote

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture

from mrok.ziti.api import ZitiClientAPI, ZitiManagementAPI
from mrok.ziti.constants import MROK_SERVICE_TAG_NAME, MROK_VERSION_TAG_NAME
from tests.conftest import SettingsFactory


@pytest.mark.asyncio
async def test_list_instances(
    mocker: MockerFixture,
    api_client: AsyncClient,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    mocker.patch(
        "mrok.controller.routes.fetch_extension_or_404", return_value={"name": "ext-1234-5678"}
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
        "mrok.controller.routes.fetch_extension_or_404", return_value={"name": "ext-1234-5678"}
    )
    mocked_register = mocker.patch(
        "mrok.controller.routes.register_instance",
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
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            MROK_SERVICE_TAG_NAME: "ext-1234-5678",
            "account": "ACC-1234-5678",
        },
        "identity": {"identity": "json"},
    }
    assert mocked_register.call_count == 1
    assert isinstance(mocked_register.mock_calls[0].args[0], ZitiManagementAPI)
    assert isinstance(mocked_register.mock_calls[0].args[1], ZitiClientAPI)
    assert mocked_register.mock_calls[0].args[2] == "ext-1234-5678"
    assert mocked_register.mock_calls[0].args[3] == "INS-1234-5678-0001"
    assert mocked_register.mock_calls[0].args[4] == {"account": "ACC-1234-5678"}


@pytest.mark.asyncio
async def test_get_instance(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
):
    mocker.patch(
        "mrok.controller.routes.fetch_extension_or_404", return_value={"name": "ext-1234-5678"}
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
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            MROK_SERVICE_TAG_NAME: "ext-1234-5678",
        },
    }


@pytest.mark.asyncio
async def test_get_instance_by_instance_id(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
):
    mocker.patch(
        "mrok.controller.routes.fetch_extension_or_404", return_value={"name": "ext-1234-5678"}
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
        "mrok.controller.routes.fetch_extension_or_404", return_value={"name": "ext-1234-5678"}
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
        "mrok.controller.routes.fetch_instance_or_404",
        return_value={"name": "ins-1234-5678.ext-1234-5678"},
    )
    mocker.patch(
        "mrok.controller.routes.unregister_instance",
    )

    response = await api_client.delete("/extensions/EXT-1234-5678/instances/INS-1234-5678-0001")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_extension_not_found(
    mocker: MockerFixture,
    api_client: AsyncClient,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    mocker.patch(
        "mrok.controller.routes.fetch_extension_or_404", return_value={"name": "ext-1234-5678"}
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
