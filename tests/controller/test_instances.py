from urllib.parse import quote

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from mrok.ziti.constants import MROK_SERVICE_TAG_NAME, MROK_VERSION_TAG_NAME
from tests.conftest import SettingsFactory


@pytest.mark.asyncio
async def test_list_instances(
    api_client: AsyncClient,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/identities?filter=tags.mrok-identity-type%3D%22instance%22&limit=10&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 15, "limit": 10, "offset": 0}},
            "data": [{"id": f"ins{i}", "name": "ins.svc"} for i in range(10)],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/identities?filter=tags.mrok-identity-type%3D%22instance%22&limit=10&offset=10",
        json={
            "meta": {"pagination": {"totalCount": 15, "limit": 10, "offset": 10}},
            "data": [{"id": f"ins{i}", "name": "ins.svc"} for i in range(11, 16)],
        },
    )
    response = await api_client.get("/instances?limit=10&offset=0")
    assert response.status_code == 200
    page_1 = response.json()
    assert len(page_1["data"]) == 10
    assert page_1["$meta"]["pagination"]["offset"] == 0

    response = await api_client.get("/instances?limit=10&offset=10")
    assert response.status_code == 200
    page_2 = response.json()
    assert len(page_2["data"]) == 5
    assert page_2["$meta"]["pagination"]["offset"] == 10

    assert sorted(page_1["data"], key=lambda x: x["id"]) != sorted(
        page_2["data"], key=lambda x: x["id"]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["online", "offline"])
async def test_get_instance(
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
    status: str,
):
    settings = settings_factory()
    query = quote(
        '(id="INS-1234-1234-0001.ext-1234-1234" or name="ins-1234-1234-0001.ext-1234-1234") '
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
                    "name": "ins-1234-1234-0001.ext-1234-1234",
                    "hasEdgeRouterConnection": status == "online",
                    "tags": {
                        MROK_VERSION_TAG_NAME: "0.0.0.dev0",
                        MROK_SERVICE_TAG_NAME: "ext-1234-1234",
                    },
                }
            ],
        },
    )

    response = await api_client.get("/instances/INS-1234-1234-0001.ext-1234-1234")
    assert response.status_code == 200
    assert response.json() == {
        "id": "ins1",
        "identity": None,
        "extension": {"id": "EXT-1234-1234"},
        "instance": {"id": "INS-1234-1234-0001"},
        "name": "ins-1234-1234-0001.ext-1234-1234",
        "status": status,
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            MROK_SERVICE_TAG_NAME: "ext-1234-1234",
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["online", "offline"])
async def test_get_instance_by_instance_id(
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
    status: str,
):
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
                    "name": "ins-1234-1234-0001.ext-1234-1234",
                    "hasEdgeRouterConnection": status == "online",
                    "tags": {
                        MROK_VERSION_TAG_NAME: "0.0.0.dev0",
                        MROK_SERVICE_TAG_NAME: "ext-1234-1234",
                    },
                }
            ],
        },
    )

    response = await api_client.get("/instances/ins1")
    assert response.status_code == 200
    assert response.json() == {
        "id": "ins1",
        "extension": {"id": "EXT-1234-1234"},
        "instance": {"id": "INS-1234-1234-0001"},
        "name": "ins-1234-1234-0001.ext-1234-1234",
        "status": status,
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            MROK_SERVICE_TAG_NAME: "ext-1234-1234",
        },
        "identity": None,
    }


@pytest.mark.asyncio
async def test_get_instance_not_found(
    settings_factory: SettingsFactory,
    api_client: AsyncClient,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    query = quote(
        '(id="INS-1234-1234-0001.ext-1234-1234" or name="ins-1234-1234-0001.ext-1234-1234") '
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

    response = await api_client.get("/instances/INS-1234-1234-0001.ext-1234-1234")
    assert response.status_code == 404
