import copy
import logging
from typing import Any

import jwt

from mrok.conf import Settings
from mrok.types.ziti import Tags
from mrok.ziti import pki
from mrok.ziti.api import ZitiClientAPI, ZitiManagementAPI
from mrok.ziti.constants import (
    MROK_IDENTITY_TYPE_TAG_NAME,
    MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE,
    MROK_IDENTITY_TYPE_TAG_VALUE_PROXY,
    MROK_SERVICE_TAG_NAME,
)
from mrok.ziti.errors import (
    ProxyIdentityAlreadyExistsError,
    ServiceNotFoundError,
    UserIdentityNotFoundError,
)
from mrok.ziti.services import register_service, unregister_service

logger = logging.getLogger("mrok.ziti")


async def register_identity(
    settings: Settings,
    mgmt_api: ZitiManagementAPI,
    client_api: ZitiClientAPI,
    service_external_id: str,
    identity_external_id: str,
    tags: Tags | None = None,
):
    service_name = service_external_id.lower()
    identity_tags = copy.copy(tags or {})
    identity_tags[MROK_SERVICE_TAG_NAME] = service_name
    identity_tags[MROK_IDENTITY_TYPE_TAG_NAME] = MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE
    service = await mgmt_api.search_service(service_name)
    if not service:
        raise ServiceNotFoundError(f"A service with name `{service_external_id}` does not exists.")

    identity_name = identity_external_id.lower()
    service_policy_name = f"{identity_name}:bind"
    self_service_policy_name = f"self.{service_policy_name}"

    identity = await mgmt_api.search_identity(identity_name)
    if identity:
        service_policy = await mgmt_api.search_service_policy(service_policy_name)
        if service_policy:
            await mgmt_api.delete_service_policy(service_policy["id"])
        service_policy = await mgmt_api.search_service_policy(self_service_policy_name)
        if service_policy:
            await mgmt_api.delete_service_policy(service_policy["id"])
        router_policy = await mgmt_api.search_router_policy(identity_name)
        if router_policy:
            await mgmt_api.delete_router_policy(router_policy["id"])
        await mgmt_api.delete_identity(identity["id"])

    identity_id = await mgmt_api.create_user_identity(identity_name, tags=identity_tags)
    identity = await mgmt_api.get_identity(identity_id)

    identity_json = await _enroll_identity(
        mgmt_api,
        client_api,
        identity_id,
        identity,
        mrok={
            "identity": identity_name,
            "extension": service_external_id,
            "instance": identity_external_id,
            "domain": settings.proxy.domain,
            "tags": identity_tags,
        },
    )

    self_service = await mgmt_api.search_service(identity_name)
    if not self_service:
        self_service = await register_service(settings, mgmt_api, identity_name, tags)

    await mgmt_api.create_bind_service_policy(service_policy_name, service["id"], identity_id)
    await mgmt_api.create_bind_service_policy(
        self_service_policy_name,
        self_service["id"],
        identity_id,
    )
    await mgmt_api.create_router_policy(identity_name, identity_id)

    return identity, identity_json


async def unregister_identity(
    settings: Settings,
    mgmt_api: ZitiManagementAPI,
    service_external_id: str,
    identity_external_id: str,
):
    service_name = service_external_id.lower()
    service = await mgmt_api.search_service(service_name)
    if not service:
        raise ServiceNotFoundError(f"A service with name `{service_external_id}` does not exists.")

    identity_name = f"{identity_external_id.lower()}.{service_name}"
    service_policy_name = f"{identity_name}:bind"

    identity = await mgmt_api.search_identity(identity_name)
    if not identity:
        raise UserIdentityNotFoundError(f"Identity `{identity_external_id}` not found.")

    self_service_policy_name = f"self.{service_policy_name}"

    service_policy = await mgmt_api.search_service_policy(self_service_policy_name)
    if service_policy:
        await mgmt_api.delete_service_policy(service_policy["id"])

    self_service = await mgmt_api.search_service(identity_name)
    if self_service:
        await unregister_service(settings, mgmt_api, identity_name)

    service_policy = await mgmt_api.search_service_policy(service_policy_name)
    if service_policy:
        await mgmt_api.delete_service_policy(service_policy["id"])
    router_policy = await mgmt_api.search_router_policy(identity_name)
    if router_policy:
        await mgmt_api.delete_router_policy(router_policy["id"])
    await mgmt_api.delete_identity(identity["id"])


async def enroll_proxy_identity(
    mgmt_api: ZitiManagementAPI,
    client_api: ZitiClientAPI,
    identity_name: str,
    tags: Tags | None = None,
):
    identity = await mgmt_api.search_identity(identity_name)
    if identity:
        raise ProxyIdentityAlreadyExistsError(
            f"A proxy identity with name `{identity_name}` already exists."
        )
    tags = tags or {}
    tags[MROK_IDENTITY_TYPE_TAG_NAME] = MROK_IDENTITY_TYPE_TAG_VALUE_PROXY
    identity_id = await mgmt_api.create_device_identity(identity_name, tags=tags)
    identity_json = await _enroll_identity(mgmt_api, client_api, identity_id)
    logger.info(f"Enrolled proxy identity '{identity_name}'")

    return identity_id, identity_json


async def _enroll_identity(
    mgmt_api: ZitiManagementAPI,
    client_api: ZitiClientAPI,
    identity_id: str,
    identity: dict[str, Any] | None = None,
    mrok: dict[str, str | dict] | None = None,
):
    if identity is None:
        identity = await mgmt_api.get_identity(identity_id)

    claims = _get_enroll_token_claims(identity)
    pkey_pem, csr_pem = pki.generate_key_and_csr(identity_id)

    enroll_response = await client_api.enroll_identity(claims["jti"], csr_pem)
    certificate_pem = enroll_response["data"]["cert"]
    ca_pem = await pki.get_ca_certificates(mgmt_api)

    return _generate_identity_json(
        client_api.base_url,
        pkey_pem,
        certificate_pem,
        ca_pem,
        mrok=mrok,
    )


def _get_enroll_token_claims(identity: dict[str, Any]):
    jwt_token = identity["enrollment"]["ott"]["jwt"]
    return jwt.decode(jwt_token, algorithms=["RS256"], options={"verify_signature": False})


def _generate_identity_json(
    ziti_api_url: str,
    pkey_pem: str,
    certificate_pem: str,
    ca_pem: str,
    mrok: dict | None = None,
) -> dict[str, Any]:
    identity = {
        "ztAPI": ziti_api_url,
        "ztAPIs": None,
        "configTypes": None,
        "id": {
            "key": f"pem:{pkey_pem}",
            "cert": f"pem:{certificate_pem}",
            "ca": f"pem:{ca_pem}",
        },
        "enableHa": False,
    }
    if mrok:
        identity["mrok"] = mrok
    return identity
