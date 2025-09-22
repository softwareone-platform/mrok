from urllib.parse import quote

import pytest
from pytest_httpx import HTTPXMock

from mrok.ziti.api import TagsType, ZitiManagementAPI
from tests.conftest import SettingsFactory


@pytest.mark.asyncio
@pytest.mark.parametrize("tags", [None, {"foo": "bar"}])
async def test_create_service(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
    tags: TagsType | None,
):
    settings = settings_factory()
    api = ZitiManagementAPI(settings)
    expected_body = {
        "name": "svc",
        "configs": ["cfgid"],
        "encryptionRequired": True,
        "tags": {"mrok": "1.0", **(tags or {})},
    }
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.ziti.url}/edge/management/v1/services",
        match_json=expected_body,
        json={"data": {"id": "service123"}},
    )
    result = await api.create_service("svc", "cfgid", tags=tags)
    assert result == "service123"


@pytest.mark.asyncio
async def test_get_service(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    api = ZitiManagementAPI(settings)
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.url}/edge/management/v1/services/service123",
        json={"data": {"id": "service123", "name": "svc"}},
    )
    result = await api.get_service("service123")
    assert result["id"] == "service123"
    assert result["name"] == "svc"


@pytest.mark.asyncio
async def test_delete_service(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    api = ZitiManagementAPI(settings)
    httpx_mock.add_response(
        method="DELETE",
        url=f"{settings.ziti.url}/edge/management/v1/services/service123",
        json={"data": {"deleted": True}},
    )
    await api.delete_service("service123")


@pytest.mark.asyncio
async def test_search_service(settings_factory: SettingsFactory, httpx_mock):
    settings = settings_factory()
    api = ZitiManagementAPI(settings)
    query = quote('(id="svc" or name="svc") and tags.mrok != null')
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.url}/edge/management/v1/services?filter={query}",
        json={
            "meta": {"pagination": {"totalCount": 1}},
            "data": [{"id": "svc1", "name": "svc"}],
        },
    )
    result = await api.search_service("svc")
    assert result is not None
    assert result["id"] == "svc1"
