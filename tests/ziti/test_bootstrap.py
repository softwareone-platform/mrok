import pytest
from pytest_mock import MockerFixture

from mrok.ziti.bootstrap import bootstrap_identity
from tests.conftest import SettingsFactory


@pytest.mark.asyncio
async def test_bootstrap_identity(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocked_mgmt_api = mocker.AsyncMock()

    mocked_mgmt_api.search_identity.return_value = None
    mocker.patch(
        "mrok.ziti.bootstrap.enroll_proxy_identity",
        new_callable=mocker.AsyncMock,
        return_value=("identity-id", {"id": "key, cert and ca", "ztAPI": "https://ziti.api"}),
    )
    mocked_mgmt_api.search_router_policy.return_value = None
    mocked_mgmt_api.create_router_policy.return_value = "router-id"
    mocked_mgmt_api.search_config_type.return_value = None
    mocked_mgmt_api.create_config_type.return_value = "config-type-id"

    identity_id, identity_json = await bootstrap_identity(
        mocked_mgmt_api,
        mocker.AsyncMock(),
        settings.proxy.identity,
        settings.proxy.mode,
        False,
        None,
    )

    assert identity_id == "identity-id"
    assert identity_json == {"id": "key, cert and ca", "ztAPI": "https://ziti.api"}


@pytest.mark.asyncio
async def test_bootstrap_identity_with_forced(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocked_mgmt_api = mocker.AsyncMock()

    mocked_mgmt_api.search_identity.return_value = {"id": "old-proxy-identity-id"}
    mocked_mgmt_api.search_router_policy.side_effect = [
        {"id": "old-router-policy-id", "name": "policy"},
        None,
    ]
    mocked_mgmt_api.delete_router_policy.return_value = None
    mocked_mgmt_api.delete_identity.return_value = None

    mocker.patch(
        "mrok.ziti.bootstrap.enroll_proxy_identity",
        new_callable=mocker.AsyncMock,
        return_value=("new-identity-id", {"id": "key, cert and ca", "ztAPI": "https://ziti.api"}),
    )

    mocked_mgmt_api.create_router_policy.return_value = "new-policy-id"
    mocked_mgmt_api.search_config_type.return_value = None
    mocked_mgmt_api.create_config_type.return_value = "config-type-id"

    identity_id, identity_json = await bootstrap_identity(
        mocked_mgmt_api,
        mocker.AsyncMock(),
        settings.proxy.identity,
        settings.proxy.mode,
        True,
        {},
    )

    assert identity_id == "new-identity-id"
    assert identity_json == {"id": "key, cert and ca", "ztAPI": "https://ziti.api"}


@pytest.mark.asyncio
async def test_bootstrap_identity_with_forced_and_no_policy(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocked_mgmt_api = mocker.AsyncMock()

    mocked_mgmt_api.search_identity.return_value = {"id": "old-proxy-identity-id"}
    mocked_mgmt_api.search_router_policy.return_value = None
    mocked_mgmt_api.create_router_policy.return_value = "policy-id"
    mocked_mgmt_api.delete_identity.return_value = None

    mocker.patch(
        "mrok.ziti.bootstrap.enroll_proxy_identity",
        new_callable=mocker.AsyncMock,
        return_value=("new-identity-id", {"id": "key, cert and ca", "ztAPI": "https://ziti.api"}),
    )

    mocked_mgmt_api.search_config_type.return_value = None
    mocked_mgmt_api.create_config_type.return_value = "config-type-id"

    identity_id, identity_json = await bootstrap_identity(
        mocked_mgmt_api,
        mocker.AsyncMock(),
        settings.proxy.identity,
        settings.proxy.mode,
        True,
        {},
    )

    assert identity_id == "new-identity-id"
    assert identity_json == {"id": "key, cert and ca", "ztAPI": "https://ziti.api"}


@pytest.mark.asyncio
async def test_bootstrap_identity_already_bootstrapped(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocked_mgmt_api = mocker.AsyncMock()

    mocked_mgmt_api.search_identity.return_value = {"id": "identity-id"}
    mocked_mgmt_api.search_router_policy.return_value = {
        "id": "router-policy-id",
        "name": "policy",
    }
    mocked_mgmt_api.search_config_type.return_value = {
        "id": "config-type-id",
        "name": "config-type",
    }

    identity_id, identity_json = await bootstrap_identity(
        mocked_mgmt_api,
        mocker.AsyncMock(),
        settings.proxy.identity,
        settings.proxy.mode,
        False,
        {},
    )

    assert identity_id == "identity-id"
    assert identity_json is None


@pytest.mark.asyncio
async def test_bootstrap_identity_with_forced_and_config_type(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocked_mgmt_api = mocker.AsyncMock()

    mocked_mgmt_api.search_identity.return_value = {"id": "old-proxy-identity-id"}
    mocked_mgmt_api.search_router_policy.side_effect = [
        {"id": "old-router-policy-id", "name": "policy"},
        None,
    ]
    mocked_mgmt_api.search_config_type.return_value = {"id": "old-config-type-id"}
    mocked_mgmt_api.delete_router_policy.return_value = None
    mocked_mgmt_api.delete_identity.return_value = None
    mocked_mgmt_api.delete_config_type.return_value = None

    mocker.patch(
        "mrok.ziti.bootstrap.enroll_proxy_identity",
        new_callable=mocker.AsyncMock,
        return_value=("new-identity-id", {"id": "key, cert and ca", "ztAPI": "https://ziti.api"}),
    )

    mocked_mgmt_api.create_router_policy.return_value = "new-policy-id"
    mocked_mgmt_api.create_config_type.return_value = "config-type-id"

    identity_id, identity_json = await bootstrap_identity(
        mocked_mgmt_api,
        mocker.AsyncMock(),
        settings.proxy.identity,
        settings.proxy.mode,
        True,
        {},
    )

    assert identity_id == "new-identity-id"
    assert identity_json == {"id": "key, cert and ca", "ztAPI": "https://ziti.api"}
