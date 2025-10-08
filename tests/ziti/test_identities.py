import pytest
from pytest_mock import MockerFixture

from mrok.ziti.constants import (
    MROK_IDENTITY_TYPE_TAG_NAME,
    MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE,
    MROK_IDENTITY_TYPE_TAG_VALUE_PROXY,
    MROK_SERVICE_TAG_NAME,
    MROK_VERSION_TAG_NAME,
)
from mrok.ziti.errors import (
    ProxyIdentityAlreadyExistsError,
    ServiceNotFoundError,
    UserIdentityNotFoundError,
)
from mrok.ziti.identities import enroll_proxy_identity, register_instance, unregister_instance


@pytest.mark.asyncio
async def test_register_instance(mocker: MockerFixture):
    mocked_jwt_decode = mocker.patch(
        "mrok.ziti.identities.jwt.decode", return_value={"jti": "jti-value"}
    )
    mocked_get_ca_certs = mocker.patch(
        "mrok.ziti.identities.pki.get_ca_certificates",
        return_value="ca-certificates-chain",
    )
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_service.return_value = {"id": "svc1"}
    mocked_mgmt_api.search_identity.return_value = None
    mocked_mgmt_api.create_user_identity.return_value = "identity-id"
    mocked_mgmt_api.get_identity.return_value = {
        "id": "identity_id",
        "name": "identity_name",
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            MROK_SERVICE_TAG_NAME: "svc1",
            "account": "ACC-1234",
        },
        "enrollment": {"ott": {"jwt": "enroll-jwt-token"}},
    }

    mocked_client_api = mocker.AsyncMock()
    mocked_client_api.base_url = "https://ziti.api"
    mocked_client_api.enroll_identity.return_value = {"data": {"cert": "identity-certificate"}}

    identity, identity_json = await register_instance(
        mocked_mgmt_api,
        mocked_client_api,
        "EXT-1234-5678",
        "INS-1234-5678-0001",
        tags={"account": "ACC-1234"},
    )
    assert identity == {
        "id": "identity_id",
        "name": "identity_name",
        "tags": {
            MROK_VERSION_TAG_NAME: "0.0.0.dev0",
            MROK_SERVICE_TAG_NAME: "svc1",
            "account": "ACC-1234",
        },
        "enrollment": {"ott": {"jwt": "enroll-jwt-token"}},
    }

    mocked_mgmt_api.search_service.assert_awaited_once_with("ext-1234-5678")
    mocked_mgmt_api.search_identity.assert_awaited_once_with("ins-1234-5678-0001.ext-1234-5678")
    mocked_mgmt_api.create_user_identity.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678",
        tags={
            MROK_SERVICE_TAG_NAME: "ext-1234-5678",
            "account": "ACC-1234",
            MROK_IDENTITY_TYPE_TAG_NAME: MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE,
        },
    )
    mocked_mgmt_api.get_identity.assert_awaited_once_with("identity-id")
    mocked_jwt_decode.assert_called_once_with(
        "enroll-jwt-token",
        algorithms=["RS256"],
        options={"verify_signature": False},
    )
    assert mocked_client_api.enroll_identity.mock_calls[0].args[0] == "jti-value"
    assert (
        mocked_client_api.enroll_identity.mock_calls[0]
        .args[1]
        .startswith("-----BEGIN CERTIFICATE REQUEST-----")
    )
    mocked_get_ca_certs.assert_awaited_once_with(mocked_mgmt_api)
    assert identity_json["ztAPI"] == "https://ziti.api"
    assert identity_json["id"]["key"].startswith("pem:-----BEGIN PRIVATE KEY-----")
    assert identity_json["id"]["cert"] == "pem:identity-certificate"
    assert identity_json["id"]["ca"] == "pem:ca-certificates-chain"

    mocked_mgmt_api.create_bind_service_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678:bind",
        "svc1",
        "identity-id",
    )
    mocked_mgmt_api.create_router_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678",
        "identity-id",
    )


@pytest.mark.asyncio
async def test_register_instance_service_not_found(mocker: MockerFixture):
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_service.return_value = None

    mocked_client_api = mocker.AsyncMock()

    with pytest.raises(ServiceNotFoundError) as cv:
        await register_instance(
            mocked_mgmt_api,
            mocked_client_api,
            "EXT-1234-5678",
            "INS-1234-5678-0001",
            tags={"account": "ACC-1234"},
        )

    assert str(cv.value) == "A service with name `EXT-1234-5678` does not exists."


@pytest.mark.asyncio
async def test_register_instance_identity_exists(mocker: MockerFixture):
    mocked_jwt_decode = mocker.patch(
        "mrok.ziti.identities.jwt.decode", return_value={"jti": "jti-value"}
    )
    mocked_get_ca_certs = mocker.patch(
        "mrok.ziti.identities.pki.get_ca_certificates",
        return_value="ca-certificates-chain",
    )
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_service.return_value = {"id": "svc1"}
    mocked_mgmt_api.search_identity.return_value = {"id": "identity-id"}
    mocked_mgmt_api.search_service_policy.return_value = {"id": "service-policy-id"}
    mocked_mgmt_api.search_router_policy.return_value = {"id": "router-policy-id"}

    mocked_mgmt_api.create_user_identity.return_value = "identity-id"
    mocked_mgmt_api.get_identity.return_value = {"enrollment": {"ott": {"jwt": "enroll-jwt-token"}}}

    mocked_client_api = mocker.AsyncMock()
    mocked_client_api.base_url = "https://ziti.api"
    mocked_client_api.enroll_identity.return_value = {"data": {"cert": "identity-certificate"}}

    _, identity_json = await register_instance(
        mocked_mgmt_api,
        mocked_client_api,
        "EXT-1234-5678",
        "INS-1234-5678-0001",
        tags={"account": "ACC-1234"},
    )

    mocked_mgmt_api.search_service.assert_awaited_once_with("ext-1234-5678")
    mocked_mgmt_api.search_identity.assert_awaited_once_with("ins-1234-5678-0001.ext-1234-5678")
    mocked_mgmt_api.create_user_identity.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678",
        tags={
            MROK_SERVICE_TAG_NAME: "ext-1234-5678",
            "account": "ACC-1234",
            MROK_IDENTITY_TYPE_TAG_NAME: MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE,
        },
    )
    mocked_mgmt_api.get_identity.assert_awaited_once_with("identity-id")
    mocked_jwt_decode.assert_called_once_with(
        "enroll-jwt-token",
        algorithms=["RS256"],
        options={"verify_signature": False},
    )
    assert mocked_client_api.enroll_identity.mock_calls[0].args[0] == "jti-value"
    assert (
        mocked_client_api.enroll_identity.mock_calls[0]
        .args[1]
        .startswith("-----BEGIN CERTIFICATE REQUEST-----")
    )
    mocked_get_ca_certs.assert_awaited_once_with(mocked_mgmt_api)
    assert identity_json["ztAPI"] == "https://ziti.api"
    assert identity_json["id"]["key"].startswith("pem:-----BEGIN PRIVATE KEY-----")
    assert identity_json["id"]["cert"] == "pem:identity-certificate"
    assert identity_json["id"]["ca"] == "pem:ca-certificates-chain"

    mocked_mgmt_api.create_bind_service_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678:bind",
        "svc1",
        "identity-id",
    )
    mocked_mgmt_api.create_router_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678",
        "identity-id",
    )
    mocked_mgmt_api.search_service_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678:bind"
    )
    mocked_mgmt_api.delete_service_policy.assert_awaited_once_with("service-policy-id")
    mocked_mgmt_api.search_router_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678"
    )
    mocked_mgmt_api.delete_router_policy.assert_awaited_once_with("router-policy-id")
    mocked_mgmt_api.delete_identity.assert_awaited_once_with("identity-id")


@pytest.mark.asyncio
async def test_register_instance_identity_exists_service_router_doesnt(mocker: MockerFixture):
    mocked_jwt_decode = mocker.patch(
        "mrok.ziti.identities.jwt.decode", return_value={"jti": "jti-value"}
    )
    mocked_get_ca_certs = mocker.patch(
        "mrok.ziti.identities.pki.get_ca_certificates",
        return_value="ca-certificates-chain",
    )
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_service.return_value = {"id": "svc1"}
    mocked_mgmt_api.search_identity.return_value = {"id": "identity-id"}
    mocked_mgmt_api.search_service_policy.return_value = None
    mocked_mgmt_api.search_router_policy.return_value = None

    mocked_mgmt_api.create_user_identity.return_value = "identity-id"
    mocked_mgmt_api.get_identity.return_value = {"enrollment": {"ott": {"jwt": "enroll-jwt-token"}}}

    mocked_client_api = mocker.AsyncMock()
    mocked_client_api.base_url = "https://ziti.api"
    mocked_client_api.enroll_identity.return_value = {"data": {"cert": "identity-certificate"}}

    _, identity_json = await register_instance(
        mocked_mgmt_api,
        mocked_client_api,
        "EXT-1234-5678",
        "INS-1234-5678-0001",
        tags={"account": "ACC-1234"},
    )

    mocked_mgmt_api.search_service.assert_awaited_once_with("ext-1234-5678")
    mocked_mgmt_api.search_identity.assert_awaited_once_with("ins-1234-5678-0001.ext-1234-5678")
    mocked_mgmt_api.create_user_identity.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678",
        tags={
            MROK_SERVICE_TAG_NAME: "ext-1234-5678",
            "account": "ACC-1234",
            MROK_IDENTITY_TYPE_TAG_NAME: MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE,
        },
    )
    mocked_mgmt_api.get_identity.assert_awaited_once_with("identity-id")
    mocked_jwt_decode.assert_called_once_with(
        "enroll-jwt-token",
        algorithms=["RS256"],
        options={"verify_signature": False},
    )
    assert mocked_client_api.enroll_identity.mock_calls[0].args[0] == "jti-value"
    assert (
        mocked_client_api.enroll_identity.mock_calls[0]
        .args[1]
        .startswith("-----BEGIN CERTIFICATE REQUEST-----")
    )
    mocked_get_ca_certs.assert_awaited_once_with(mocked_mgmt_api)
    assert identity_json["ztAPI"] == "https://ziti.api"
    assert identity_json["id"]["key"].startswith("pem:-----BEGIN PRIVATE KEY-----")
    assert identity_json["id"]["cert"] == "pem:identity-certificate"
    assert identity_json["id"]["ca"] == "pem:ca-certificates-chain"

    mocked_mgmt_api.create_bind_service_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678:bind",
        "svc1",
        "identity-id",
    )
    mocked_mgmt_api.create_router_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678",
        "identity-id",
    )
    mocked_mgmt_api.search_service_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678:bind"
    )
    mocked_mgmt_api.delete_service_policy.assert_not_awaited()
    mocked_mgmt_api.search_router_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678"
    )
    mocked_mgmt_api.delete_router_policy.assert_not_awaited()
    mocked_mgmt_api.delete_identity.assert_awaited_once_with("identity-id")


@pytest.mark.asyncio
async def test_unregister_instance(
    mocker: MockerFixture,
):
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_service.return_value = {"id": "svc1"}
    mocked_mgmt_api.search_identity.return_value = {"id": "identity-id"}
    mocked_mgmt_api.search_service_policy.return_value = {"id": "service-policy-id"}
    mocked_mgmt_api.search_router_policy.return_value = {"id": "router-policy-id"}

    await unregister_instance(
        mocked_mgmt_api,
        "EXT-1234-5678",
        "INS-1234-5678-0001",
    )

    mocked_mgmt_api.search_service.assert_awaited_once_with("ext-1234-5678")
    mocked_mgmt_api.search_identity.assert_awaited_once_with("ins-1234-5678-0001.ext-1234-5678")

    mocked_mgmt_api.search_service_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678:bind"
    )
    mocked_mgmt_api.delete_service_policy.assert_awaited_once_with("service-policy-id")
    mocked_mgmt_api.search_router_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678"
    )
    mocked_mgmt_api.delete_router_policy.assert_awaited_once_with("router-policy-id")
    mocked_mgmt_api.delete_identity.assert_awaited_once_with("identity-id")


@pytest.mark.asyncio
async def test_unregister_instance_service_not_found(mocker: MockerFixture):
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_service.return_value = None

    with pytest.raises(ServiceNotFoundError) as cv:
        await unregister_instance(
            mocked_mgmt_api,
            "EXT-1234-5678",
            "INS-1234-5678-0001",
        )

    assert str(cv.value) == "A service with name `EXT-1234-5678` does not exists."


@pytest.mark.asyncio
async def test_unregister_instance_instance_not_found(mocker: MockerFixture):
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_service.return_value = {"id": "svc1"}
    mocked_mgmt_api.search_identity.return_value = None

    with pytest.raises(UserIdentityNotFoundError) as cv:
        await unregister_instance(
            mocked_mgmt_api,
            "EXT-1234-5678",
            "INS-1234-5678-0001",
        )

    assert str(cv.value) == "Instance `INS-1234-5678-0001` not found."


@pytest.mark.asyncio
async def test_unregister_instance_policies_not_found(
    mocker: MockerFixture,
):
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_service.return_value = {"id": "svc1"}
    mocked_mgmt_api.search_identity.return_value = {"id": "identity-id"}
    mocked_mgmt_api.search_service_policy.return_value = None
    mocked_mgmt_api.search_router_policy.return_value = None

    await unregister_instance(
        mocked_mgmt_api,
        "EXT-1234-5678",
        "INS-1234-5678-0001",
    )

    mocked_mgmt_api.search_service.assert_awaited_once_with("ext-1234-5678")
    mocked_mgmt_api.search_identity.assert_awaited_once_with("ins-1234-5678-0001.ext-1234-5678")

    mocked_mgmt_api.search_service_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678:bind"
    )
    mocked_mgmt_api.delete_service_policy.assert_not_awaited()
    mocked_mgmt_api.search_router_policy.assert_awaited_once_with(
        "ins-1234-5678-0001.ext-1234-5678"
    )
    mocked_mgmt_api.delete_router_policy.assert_not_awaited()
    mocked_mgmt_api.delete_identity.assert_awaited_once_with("identity-id")


@pytest.mark.asyncio
async def test_enroll_proxy_identity(mocker: MockerFixture):
    mocked_jwt_decode = mocker.patch(
        "mrok.ziti.identities.jwt.decode", return_value={"jti": "jti-value"}
    )
    mocked_get_ca_certs = mocker.patch(
        "mrok.ziti.identities.pki.get_ca_certificates",
        return_value="ca-certificates-chain",
    )
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_identity.return_value = None
    mocked_mgmt_api.create_device_identity.return_value = "identity-id"
    mocked_mgmt_api.get_identity.return_value = {"enrollment": {"ott": {"jwt": "enroll-jwt-token"}}}

    mocked_client_api = mocker.AsyncMock()
    mocked_client_api.base_url = "https://ziti.api"
    mocked_client_api.enroll_identity.return_value = {"data": {"cert": "identity-certificate"}}

    _, identity_json = await enroll_proxy_identity(
        mocked_mgmt_api,
        mocked_client_api,
        "mrok-proxy",
        tags={"test": "tag"},
    )

    mocked_mgmt_api.search_identity.assert_awaited_once_with("mrok-proxy")
    mocked_mgmt_api.create_device_identity.assert_awaited_once_with(
        "mrok-proxy",
        tags={"test": "tag", MROK_IDENTITY_TYPE_TAG_NAME: MROK_IDENTITY_TYPE_TAG_VALUE_PROXY},
    )
    mocked_mgmt_api.get_identity.assert_awaited_once_with("identity-id")
    mocked_jwt_decode.assert_called_once_with(
        "enroll-jwt-token",
        algorithms=["RS256"],
        options={"verify_signature": False},
    )
    assert mocked_client_api.enroll_identity.mock_calls[0].args[0] == "jti-value"
    assert (
        mocked_client_api.enroll_identity.mock_calls[0]
        .args[1]
        .startswith("-----BEGIN CERTIFICATE REQUEST-----")
    )
    mocked_get_ca_certs.assert_awaited_once_with(mocked_mgmt_api)
    assert identity_json["ztAPI"] == "https://ziti.api"
    assert identity_json["id"]["key"].startswith("pem:-----BEGIN PRIVATE KEY-----")
    assert identity_json["id"]["cert"] == "pem:identity-certificate"
    assert identity_json["id"]["ca"] == "pem:ca-certificates-chain"


@pytest.mark.asyncio
async def test_enroll_proxy_identity_already_exists(mocker: MockerFixture):
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.search_identity.return_value = {"id": "identity-id"}

    with pytest.raises(ProxyIdentityAlreadyExistsError) as cv:
        await enroll_proxy_identity(
            mocked_mgmt_api,
            mocker.AsyncMock(),
            "mrok-proxy",
            tags={"test": "tag"},
        )

    assert str(cv.value) == "A proxy identity with name `mrok-proxy` already exists."
