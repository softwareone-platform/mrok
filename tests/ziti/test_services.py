import pytest
from pytest_mock import MockerFixture

from mrok.types.ziti import Tags
from mrok.ziti.services import (
    ConfigTypeNotFoundError,
    ProxyIdentityNotFoundError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
    register_service,
    unregister_service,
)
from tests.conftest import SettingsFactory


@pytest.mark.asyncio
async def test_register_extension(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_identity.return_value = {"id": "proxy_identity_id"}
    mocked_api.search_config_type.return_value = {"id": "config_type_id"}
    mocked_api.search_config.return_value = None
    mocked_api.create_config.return_value = "config_id"
    mocked_api.search_service.return_value = None
    mocked_api.create_service.return_value = "service_id"
    mocked_api.get_service.return_value = {"id": "service_id"}
    mocked_api.search_service_policy.return_value = None
    mocked_api.search_service_router_policy.return_value = None

    tags: Tags = {"tag": "my-tag"}

    await register_service(settings, mocked_api, "EXT-1234", tags)

    mocked_api.search_identity.assert_awaited_once_with(settings.proxy.identity)
    mocked_api.search_config_type.assert_awaited_once_with(f"{settings.proxy.mode}.proxy.v1")
    mocked_api.search_config.assert_awaited_once_with("ext-1234")
    mocked_api.create_config.assert_awaited_once_with(
        "ext-1234",
        "config_type_id",
        tags=tags,
    )
    mocked_api.search_service.assert_called_once_with("ext-1234")
    mocked_api.create_service.assert_called_once_with("ext-1234", "config_id", tags=tags)
    mocked_api.get_service.assert_awaited_once_with("service_id")
    mocked_api.search_service_policy.assert_called_once_with(
        f"ext-1234:{settings.proxy.identity}:dial"
    )
    mocked_api.create_dial_service_policy.assert_called_once_with(
        f"ext-1234:{settings.proxy.identity}:dial",
        "service_id",
        "proxy_identity_id",
        tags=tags,
    )
    mocked_api.search_service_router_policy.assert_awaited_once_with("ext-1234")
    mocked_api.create_service_router_policy.assert_awaited_once_with(
        "ext-1234",
        "service_id",
        tags=tags,
    )


@pytest.mark.asyncio
async def test_register_extension_no_proxy_identity(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_identity.return_value = None

    with pytest.raises(ProxyIdentityNotFoundError) as cv:
        await register_service(settings, mocked_api, "EXT-1234", None)
    assert str(cv.value) == f"Identity for proxy `{settings.proxy.identity}` not found."


@pytest.mark.asyncio
async def test_register_extension_no_config_type(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_identity.return_value = {"id": "proxy_identity_id"}
    mocked_api.search_config_type.return_value = None

    with pytest.raises(ConfigTypeNotFoundError) as cv:
        await register_service(settings, mocked_api, "EXT-1234", None)
    assert str(cv.value) == f"Config type `{settings.proxy.mode}.proxy.v1` not found."


@pytest.mark.asyncio
async def test_register_extension_config_exists(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_identity.return_value = {"id": "proxy_identity_id"}
    mocked_api.search_config_type.return_value = {"id": "config_type_id"}
    mocked_api.search_config.return_value = {"id": "config_id"}
    mocked_api.search_service.return_value = None
    mocked_api.create_service.return_value = "service_id"
    mocked_api.get_service.return_value = {"id": "service_id"}
    mocked_api.search_service_policy.return_value = None
    mocked_api.search_service_router_policy.return_value = None

    tags: Tags = {"tag": "my-tag"}

    await register_service(settings, mocked_api, "EXT-1234", tags)

    mocked_api.search_identity.assert_awaited_once_with(settings.proxy.identity)
    mocked_api.search_config_type.assert_awaited_once_with(f"{settings.proxy.mode}.proxy.v1")
    mocked_api.search_config.assert_awaited_once_with("ext-1234")
    mocked_api.create_config.assert_not_awaited()
    mocked_api.search_service.assert_called_once_with("ext-1234")
    mocked_api.create_service.assert_called_once_with("ext-1234", "config_id", tags=tags)
    mocked_api.search_service_policy.assert_called_once_with(
        f"ext-1234:{settings.proxy.identity}:dial"
    )
    mocked_api.create_dial_service_policy.assert_called_once_with(
        f"ext-1234:{settings.proxy.identity}:dial",
        "service_id",
        "proxy_identity_id",
        tags=tags,
    )
    mocked_api.search_service_router_policy.assert_awaited_once_with("ext-1234")
    mocked_api.create_service_router_policy.assert_awaited_once_with(
        "ext-1234",
        "service_id",
        tags=tags,
    )


@pytest.mark.asyncio
async def test_register_extension_service_exists(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_identity.return_value = {"id": "proxy_identity_id"}
    mocked_api.search_config_type.return_value = {"id": "config_type_id"}
    mocked_api.search_config.return_value = {"id": "config_id"}
    mocked_api.search_service.return_value = {"id": "service_id"}
    mocked_api.search_service_policy.return_value = None
    mocked_api.search_service_router_policy.return_value = None

    tags: Tags = {"tag": "my-tag"}

    await register_service(settings, mocked_api, "EXT-1234", tags)

    mocked_api.search_identity.assert_awaited_once_with(settings.proxy.identity)
    mocked_api.search_config_type.assert_awaited_once_with(f"{settings.proxy.mode}.proxy.v1")
    mocked_api.search_config.assert_awaited_once_with("ext-1234")
    mocked_api.create_config.assert_not_awaited()
    mocked_api.search_service.assert_called_once_with("ext-1234")
    mocked_api.create_service.assert_not_awaited()
    mocked_api.get_service.assert_not_awaited()
    mocked_api.search_service_policy.assert_called_once_with(
        f"ext-1234:{settings.proxy.identity}:dial"
    )
    mocked_api.create_dial_service_policy.assert_called_once_with(
        f"ext-1234:{settings.proxy.identity}:dial",
        "service_id",
        "proxy_identity_id",
        tags=tags,
    )
    mocked_api.search_service_router_policy.assert_awaited_once_with("ext-1234")
    mocked_api.create_service_router_policy.assert_awaited_once_with(
        "ext-1234",
        "service_id",
        tags=tags,
    )


@pytest.mark.asyncio
async def test_register_extension_dial_policy_exists(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_identity.return_value = {"id": "proxy_identity_id"}
    mocked_api.search_config_type.return_value = {"id": "config_type_id"}
    mocked_api.search_config.return_value = {"id": "config_id"}
    mocked_api.search_service.return_value = {"id": "service_id"}
    mocked_api.search_service_policy.return_value = {"id": "policy_id"}
    mocked_api.search_service_router_policy.return_value = None

    tags: Tags = {"tag": "my-tag"}

    await register_service(settings, mocked_api, "EXT-1234", tags)

    mocked_api.search_identity.assert_awaited_once_with(settings.proxy.identity)
    mocked_api.search_config_type.assert_awaited_once_with(f"{settings.proxy.mode}.proxy.v1")
    mocked_api.search_config.assert_awaited_once_with("ext-1234")
    mocked_api.create_config.assert_not_awaited()
    mocked_api.search_service.assert_called_once_with("ext-1234")
    mocked_api.create_service.assert_not_awaited()
    mocked_api.get_service.assert_not_awaited()
    mocked_api.search_service_policy.assert_called_once_with(
        f"ext-1234:{settings.proxy.identity}:dial"
    )
    mocked_api.create_dial_service_policy.assert_not_awaited()
    mocked_api.search_service_router_policy.assert_awaited_once_with("ext-1234")
    mocked_api.create_service_router_policy.assert_awaited_once_with(
        "ext-1234",
        "service_id",
        tags=tags,
    )


@pytest.mark.asyncio
async def test_register_extension_router_policy_exists(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_identity.return_value = {"id": "proxy_identity_id"}
    mocked_api.search_config_type.return_value = {"id": "config_type_id"}
    mocked_api.search_config.return_value = {"id": "config_id"}
    mocked_api.search_service.return_value = {"id": "service_id"}
    mocked_api.search_service_policy.return_value = {"id": "policy_id"}
    mocked_api.search_service_router_policy.return_value = {"id": "policy_id"}

    tags: Tags = {"tag": "my-tag"}

    with pytest.raises(ServiceAlreadyRegisteredError) as cv:
        await register_service(settings, mocked_api, "EXT-1234", tags)
    assert str(cv.value) == "Service `EXT-1234` already registered."

    mocked_api.search_identity.assert_awaited_once_with(settings.proxy.identity)
    mocked_api.search_config_type.assert_awaited_once_with(f"{settings.proxy.mode}.proxy.v1")
    mocked_api.search_config.assert_awaited_once_with("ext-1234")
    mocked_api.create_config.assert_not_awaited()
    mocked_api.search_service.assert_called_once_with("ext-1234")
    mocked_api.create_service.assert_not_awaited()
    mocked_api.get_service.assert_not_awaited()
    mocked_api.search_service_policy.assert_called_once_with(
        f"ext-1234:{settings.proxy.identity}:dial"
    )
    mocked_api.create_dial_service_policy.assert_not_awaited()
    mocked_api.search_service_router_policy.assert_awaited_once_with("ext-1234")
    mocked_api.create_service_router_policy.assert_not_awaited()


@pytest.mark.asyncio
async def test_unregister_extension(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_service.return_value = {"id": "service_id"}
    mocked_api.search_service_router_policy.return_value = {"id": "router_policy_id"}
    mocked_api.search_service_policy.return_value = {"id": "service_policy_id"}
    mocked_api.search_config.return_value = {"id": "config_id"}

    await unregister_service(settings, mocked_api, "EXT-1234")

    mocked_api.delete_service_router_policy.assert_awaited_once_with("router_policy_id")
    mocked_api.delete_service_policy.assert_awaited_once_with("service_policy_id")
    mocked_api.delete_config.assert_awaited_once_with("config_id")
    mocked_api.delete_service.assert_awaited_once_with("service_id")


@pytest.mark.asyncio
async def test_unregister_extension_not_found(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_service.return_value = None

    with pytest.raises(ServiceNotFoundError) as cv:
        await unregister_service(settings, mocked_api, "EXT-1234")
    assert str(cv.value) == "Service `EXT-1234` not found."


@pytest.mark.asyncio
async def test_unregister_extension_router_policy_doesnt_exist(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_service.return_value = {"id": "service_id"}
    mocked_api.search_service_router_policy.return_value = None
    mocked_api.search_service_policy.return_value = {"id": "service_policy_id"}
    mocked_api.search_config.return_value = {"id": "config_id"}

    await unregister_service(settings, mocked_api, "EXT-1234")

    mocked_api.delete_service_router_policy.assert_not_awaited()
    mocked_api.delete_service_policy.assert_awaited_once_with("service_policy_id")
    mocked_api.delete_config.assert_awaited_once_with("config_id")
    mocked_api.delete_service.assert_awaited_once_with("service_id")


@pytest.mark.asyncio
async def test_unregister_extension_service_policy_doesnt_exist(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_service.return_value = {"id": "service_id"}
    mocked_api.search_service_router_policy.return_value = None
    mocked_api.search_service_policy.return_value = None
    mocked_api.search_config.return_value = {"id": "config_id"}

    await unregister_service(settings, mocked_api, "EXT-1234")

    mocked_api.delete_service_router_policy.assert_not_awaited()
    mocked_api.delete_service_policy.assert_not_awaited()
    mocked_api.delete_config.assert_awaited_once_with("config_id")
    mocked_api.delete_service.assert_awaited_once_with("service_id")


@pytest.mark.asyncio
async def test_unregister_extension_config_doesnt_exist(
    mocker: MockerFixture, settings_factory: SettingsFactory
):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.search_service.return_value = {"id": "service_id"}
    mocked_api.search_service_router_policy.return_value = None
    mocked_api.search_service_policy.return_value = None
    mocked_api.search_config.return_value = None

    await unregister_service(settings, mocked_api, "EXT-1234")

    mocked_api.delete_service_router_policy.assert_not_awaited()
    mocked_api.delete_service_policy.assert_not_awaited()
    mocked_api.delete_config.assert_not_awaited()
    mocked_api.delete_service.assert_awaited_once_with("service_id")
