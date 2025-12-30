from typing import Any
from urllib.parse import quote

import pytest
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture

from mrok.types.ziti import Tags
from mrok.ziti.api import (
    ZitiAuthError,
    ZitiBadRequestError,
    ZitiClientAPI,
    ZitiIdentityAuthContext,
    ZitiManagementAPI,
)
from mrok.ziti.constants import MROK_VERSION_TAG_NAME
from tests.conftest import SettingsFactory


@pytest.mark.asyncio
@pytest.mark.parametrize("tags", [None, {"foo": "bar"}])
async def test_create(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
    tags: Tags | None,
):
    settings = settings_factory()
    expected_body = {
        "test": "payload",
        "tags": {MROK_VERSION_TAG_NAME: "0.0.0.dev0", **(tags or {})},
    }
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.ziti.api.management}/edge/management/v1/services",
        match_json=expected_body,
        json={"data": {"id": "service123"}},
    )
    async with ZitiManagementAPI(settings) as api:
        result = await api.create("/services", {"test": "payload"}, tags)
        assert result == "service123"


@pytest.mark.asyncio
async def test_create_bad_request(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
    ziti_bad_request_error: dict[str, Any],
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.ziti.api.management}/edge/management/v1/services",
        status_code=400,
        json=ziti_bad_request_error,
    )
    async with ZitiManagementAPI(settings) as api:
        with pytest.raises(ZitiBadRequestError) as cv:
            await api.create("/services", {"test": "payload"}, None)
    assert str(cv.value) == "error_code - error_message (field_name: field_error)"


@pytest.mark.asyncio
async def test_get(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services/service123",
        json={"data": {"id": "service123", "name": "svc"}},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services/service123/policies",
        json={"data": {"id": "policy123", "name": "plc"}},
    )

    async with ZitiManagementAPI(settings) as api:
        result = await api.get("/services", "service123")
    assert result["id"] == "service123"
    assert result["name"] == "svc"

    async with ZitiManagementAPI(settings) as api:
        result = await api.get("/services", "service123", "policies")
    assert result["id"] == "policy123"
    assert result["name"] == "plc"


@pytest.mark.asyncio
async def test_delete(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="DELETE",
        url=f"{settings.ziti.api.management}/edge/management/v1/services/service123",
        json={"data": {"deleted": True}},
    )
    async with ZitiManagementAPI(settings) as api:
        await api.delete("/services", "service123")


@pytest.mark.asyncio
async def test_search_by_id_or_name(settings_factory: SettingsFactory, httpx_mock: HTTPXMock):
    settings = settings_factory()
    query = quote(f'(id="svc" or name="svc") and tags.{MROK_VERSION_TAG_NAME} != null')
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services?filter={query}",
        json={
            "meta": {"pagination": {"totalCount": 1}},
            "data": [{"id": "svc1", "name": "svc"}],
        },
    )
    async with ZitiManagementAPI(settings) as api:
        result = await api.search_by_id_or_name("/services", "svc")
    assert result is not None
    assert result["id"] == "svc1"


@pytest.mark.asyncio
async def test_search_by_id_or_name_no_results(
    settings_factory: SettingsFactory, httpx_mock: HTTPXMock
):
    settings = settings_factory()
    query = quote(f'(id="svc" or name="svc") and tags.{MROK_VERSION_TAG_NAME} != null')
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services?filter={query}",
        json={
            "meta": {"pagination": {"totalCount": 0}},
            "data": [],
        },
    )
    async with ZitiManagementAPI(settings) as api:
        result = await api.search_by_id_or_name("/services", "svc")
    assert result is None


@pytest.mark.asyncio
async def test_search_by_id_or_name_bad_request(
    settings_factory: SettingsFactory, httpx_mock: HTTPXMock, ziti_bad_request_error: dict[str, Any]
):
    settings = settings_factory()
    query = quote(f'(id="svc" or name="svc") and tags.{MROK_VERSION_TAG_NAME} != null')
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services?filter={query}",
        status_code=400,
        json=ziti_bad_request_error,
    )
    async with ZitiManagementAPI(settings) as api:
        with pytest.raises(ZitiBadRequestError) as cv:
            await api.search_by_id_or_name("/services", "svc")
    assert str(cv.value) == "error_code - error_message (field_name: field_error)"


@pytest.mark.asyncio
async def test_collection_iterator(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
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
    async with ZitiManagementAPI(settings) as api:
        results = [item async for item in api.collection_iterator("/services")]
    assert len(results) == 10


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "endpoint"),
    [
        ("get_service", "/services"),
        ("get_identity", "/identities"),
    ],
)
async def test_get_methods(
    mocker: MockerFixture, settings_factory: SettingsFactory, method_name: str, endpoint: str
):
    settings = settings_factory()
    mocked_get = mocker.patch.object(ZitiManagementAPI, "get", return_value={"returned": "object"})
    async with ZitiManagementAPI(settings) as api:
        method = getattr(api, method_name)
        result = await method("id")
    assert result == {"returned": "object"}
    mocked_get.assert_awaited_once_with(endpoint, "id")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "endpoint"),
    [
        ("search_service_router_policy", "/service-edge-router-policies"),
        ("search_router_policy", "/edge-router-policies"),
        ("search_service", "/services"),
        ("search_identity", "/identities"),
        ("search_config_type", "/config-types"),
        ("search_service_policy", "/service-policies"),
        ("search_config", "/configs"),
    ],
)
async def test_search_methods(
    mocker: MockerFixture, settings_factory: SettingsFactory, method_name: str, endpoint: str
):
    settings = settings_factory()
    mocked_search = mocker.patch.object(
        ZitiManagementAPI, "search_by_id_or_name", return_value={"returned": "object"}
    )
    async with ZitiManagementAPI(settings) as api:
        method = getattr(api, method_name)
        result = await method("id")
    assert result == {"returned": "object"}
    mocked_search.assert_awaited_once_with(endpoint, "id")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "endpoint"),
    [
        ("delete_config", "/configs"),
        ("delete_config_type", "/config-types"),
        ("delete_service_policy", "/service-policies"),
        ("delete_service_router_policy", "/service-edge-router-policies"),
        ("delete_router_policy", "/edge-router-policies"),
        ("delete_service", "/services"),
        ("delete_identity", "/identities"),
    ],
)
async def test_delete_methods(
    mocker: MockerFixture, settings_factory: SettingsFactory, method_name: str, endpoint: str
):
    settings = settings_factory()
    mocked_deleted = mocker.patch.object(ZitiManagementAPI, "delete")
    async with ZitiManagementAPI(settings) as api:
        method = getattr(api, method_name)
        await method("id")

    mocked_deleted.assert_awaited_once_with(endpoint, "id")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "endpoint"),
    [
        ("services", "/services"),
        ("identities", "/identities"),
    ],
)
async def test_iterator_methods(
    mocker: MockerFixture, settings_factory: SettingsFactory, method_name: str, endpoint: str
):
    settings = settings_factory()
    mocked_awaitable = mocker.AsyncMock()
    mocked_collection_iterator = mocker.patch.object(
        ZitiManagementAPI, "collection_iterator", return_value=mocked_awaitable
    )
    async with ZitiManagementAPI(settings) as api:
        method = getattr(api, method_name)
        awaitable = method()

    mocked_collection_iterator.assert_called_once_with(endpoint, params=None)
    assert awaitable == mocked_awaitable


@pytest.mark.asyncio
async def test_create_config(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_create = mocker.patch.object(ZitiManagementAPI, "create", return_value="id")
    async with ZitiManagementAPI(settings) as api:
        config_id = await api.create_config("my-config", "my-config-type-id")
    assert config_id == "id"
    mocked_create.assert_awaited_once_with(
        "/configs",
        {
            "configTypeId": "my-config-type-id",
            "name": "my-config",
            "data": {
                "auth_scheme": "none",
                "basic_auth": None,
                "interstitial": True,
                "oauth": None,
            },
        },
        None,
    )


@pytest.mark.asyncio
async def test_create_config_type(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_create = mocker.patch.object(ZitiManagementAPI, "create", return_value="id")
    async with ZitiManagementAPI(settings) as api:
        config_type_id = await api.create_config_type("my-config-type")
    assert config_type_id == "id"
    mocked_create.assert_awaited_once_with(
        "/config-types",
        {
            "name": "my-config-type",
            "schema": {},
        },
        None,
    )


@pytest.mark.asyncio
async def test_create_service(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_create = mocker.patch.object(ZitiManagementAPI, "create", return_value="id")
    async with ZitiManagementAPI(settings) as api:
        service_id = await api.create_service("my-service", "my-config-id")
    assert service_id == "id"
    mocked_create.assert_awaited_once_with(
        "/services",
        {
            "name": "my-service",
            "configs": ["my-config-id"],
            "encryptionRequired": True,
        },
        None,
    )


@pytest.mark.asyncio
async def test_create_service_router_policy(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_create = mocker.patch.object(ZitiManagementAPI, "create", return_value="id")
    async with ZitiManagementAPI(settings) as api:
        policy_id = await api.create_service_router_policy("my-policy", "my-service")
    assert policy_id == "id"
    mocked_create.assert_awaited_once_with(
        "/service-edge-router-policies",
        {
            "name": "my-policy",
            "edgeRouterRoles": ["#all"],
            "serviceRoles": ["@my-service"],
            "semantic": "AllOf",
        },
        None,
    )


@pytest.mark.asyncio
async def test_create_router_policy(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_create = mocker.patch.object(ZitiManagementAPI, "create", return_value="id")
    async with ZitiManagementAPI(settings) as api:
        policy_id = await api.create_router_policy("my-policy", "my-identity")
    assert policy_id == "id"
    mocked_create.assert_awaited_once_with(
        "/edge-router-policies",
        {
            "name": "my-policy",
            "edgeRouterRoles": ["#all"],
            "identityRoles": ["@my-identity"],
            "semantic": "AllOf",
        },
        None,
    )


@pytest.mark.asyncio
async def test_create_dial_service_policy(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_create = mocker.patch.object(ZitiManagementAPI, "create", return_value="id")
    async with ZitiManagementAPI(settings) as api:
        policy_id = await api.create_dial_service_policy("my-policy", "my-service", "my-identity")
    assert policy_id == "id"
    mocked_create.assert_awaited_once_with(
        "/service-policies",
        {
            "name": "my-policy",
            "type": "Dial",
            "serviceRoles": ["@my-service"],
            "identityRoles": ["@my-identity"],
            "semantic": "AllOf",
        },
        None,
    )


@pytest.mark.asyncio
async def test_create_bind_service_policy(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_create = mocker.patch.object(ZitiManagementAPI, "create", return_value="id")
    async with ZitiManagementAPI(settings) as api:
        policy_id = await api.create_bind_service_policy("my-policy", "my-service", "my-identity")
    assert policy_id == "id"
    mocked_create.assert_awaited_once_with(
        "/service-policies",
        {
            "name": "my-policy",
            "type": "Bind",
            "serviceRoles": ["@my-service"],
            "identityRoles": ["@my-identity"],
            "semantic": "AllOf",
        },
        None,
    )


@pytest.mark.asyncio
async def test_create_user_identity(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_create = mocker.patch.object(ZitiManagementAPI, "create", return_value="id")
    async with ZitiManagementAPI(settings) as api:
        policy_id = await api.create_user_identity("my-identity")
    assert policy_id == "id"
    mocked_create.assert_awaited_once_with(
        "/identities",
        {
            "name": "my-identity",
            "type": "User",
            "isAdmin": False,
            "enrollment": {"ott": True},
        },
        None,
    )


@pytest.mark.asyncio
async def test_create_device_identity(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_create = mocker.patch.object(ZitiManagementAPI, "create", return_value="id")
    async with ZitiManagementAPI(settings) as api:
        policy_id = await api.create_device_identity("my-identity")
    assert policy_id == "id"
    mocked_create.assert_awaited_once_with(
        "/identities",
        {
            "name": "my-identity",
            "type": "Device",
            "isAdmin": False,
            "enrollment": {"ott": True},
        },
        None,
    )


@pytest.mark.asyncio
async def test_fetch_ca_certs(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/.well-known/est/cacerts",
        text="-----BEGIN CERTIFICATE----\n...\n-----END CERTIFICATE-----",
    )
    async with ZitiManagementAPI(settings) as api:
        result = await api.fetch_ca_certificates()
    assert result == "-----BEGIN CERTIFICATE----\n...\n-----END CERTIFICATE-----"


@pytest.mark.asyncio
async def test_password_auth(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services/service123",
        status_code=401,
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.ziti.api.management}/edge/management/v1/authenticate?method=password",
        match_json={
            "username": settings.ziti.auth.username,
            "password": settings.ziti.auth.password,
        },
        status_code=200,
        json={"data": {"token": "auth-token"}},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services/service123",
        match_headers={"zt-session": "auth-token"},
        json={"data": {"id": "service123", "name": "svc"}},
    )
    async with ZitiManagementAPI(settings) as api:
        result = await api.get("/services", "service123")
    assert result["id"] == "service123"
    assert result["name"] == "svc"


def test_zitiidentityauthcontext(mocker: MockerFixture, ziti_identity_file: str):
    mocked_ssl_context = mocker.MagicMock()
    mocked_create_ssl_ctx = mocker.patch(
        "mrok.ziti.api.ssl.create_default_context", return_value=mocked_ssl_context
    )
    ZitiIdentityAuthContext(ziti_identity_file)
    mocked_create_ssl_ctx.assert_called_once()
    mocked_ssl_context.load_cert_chain.assert_called_once()


@pytest.mark.asyncio
async def test_identity_auth(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory(
        ziti={
            "api": {"management": "https://ziti.example.com"},
            "read_timeout": 10,
            "ssl_verify": True,
            "auth": {"identity": "my-identity.json"},
        }
    )
    mocked_ctx = mocker.patch("mrok.ziti.api.ZitiIdentityAuthContext")
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services/service123",
        status_code=401,
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.ziti.api.management}/edge/management/v1/authenticate?method=cert",
        status_code=200,
        json={"data": {"token": "auth-token"}},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.ziti.api.management}/edge/management/v1/services/service123",
        match_headers={"zt-session": "auth-token"},
        json={"data": {"id": "service123", "name": "svc"}},
    )
    async with ZitiManagementAPI(settings) as api:
        result = await api.get("/services", "service123")
    assert result["id"] == "service123"
    assert result["name"] == "svc"
    mocked_ctx.assert_called_once_with("my-identity.json")


def test_invalid_auth(
    settings_factory: SettingsFactory,
):
    settings = settings_factory(
        ziti={
            "url": "https://ziti.example.com",
            "read_timeout": 10,
            "ssl_verify": True,
            "auth": {},
        }
    )
    with pytest.raises(ZitiAuthError) as cv:
        _ = ZitiManagementAPI(settings).auth

    assert str(cv.value) == "Unsupported authentication method for OpenZiti."


@pytest.mark.asyncio
async def test_enroll_identity(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.ziti.api.client}/edge/client/v1/enroll?method=ott&token=jti",
        status_code=200,
        match_content=b"csr",
        match_headers={"Content-Type": "application/x-pem-file"},
        json={"identity": "whatever"},
    )
    async with ZitiClientAPI(settings) as api:
        result = await api.enroll_identity("jti", "csr")

    assert result == {"identity": "whatever"}
