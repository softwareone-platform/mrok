from typing import Any

import jwt

from mrok.conf import get_settings
from mrok.ziti import pki
from mrok.ziti.api import ZitiClientAPI, ZitiManagementAPI
from mrok.ziti.errors import ProxyIdentityAlreadyExistsError, ServiceNotFoundError


async def enroll_instance_identity(
    extension_id: str,
    instance_id: str,
    tags: dict[str, str] | None = None,
):
    settings = get_settings()
    mgmt_api = ZitiManagementAPI(settings)
    client_api = ZitiClientAPI(settings)
    service = await mgmt_api.search_service(extension_id)
    if not service:
        raise ServiceNotFoundError(f"A service with name {extension_id} does not exists.")

    identity_name = f"{instance_id}.{extension_id}"
    service_policy_name = f"{identity_name}:bind"

    identity = await mgmt_api.search_identity(identity_name)
    if identity:
        await mgmt_api.delete_identity(identity["id"])
        service_policy = await mgmt_api.search_service_policy(service_policy_name)
        if service_policy:
            await mgmt_api.delete_service_policy(service_policy["id"])

    identity_id = await mgmt_api.create_user_identity(identity_name, tags=tags)
    identity = await mgmt_api.get_identity(identity_id)

    claims = _get_enroll_token_claims(identity)

    pkey_pem, csr_pem = pki.generate_key_and_csr(identity_id)

    enroll_response = await client_api.enroll_identity(claims["jti"], csr_pem)
    certificate_pem = enroll_response["data"]["cert"]
    ca_pem = await pki.get_ca_certificates(mgmt_api)

    await mgmt_api.create_bind_service_policy(service_policy_name, service["id"], identity_id)
    await mgmt_api.create_router_policy(identity_name, identity_id)

    return _generate_identity_json(
        client_api.base_url,
        pkey_pem,
        certificate_pem,
        ca_pem,
    )


async def enroll_proxy_identity(
    identity_name: str,
    tags: dict[str, str] | None = None,
):
    settings = get_settings()
    mgmt_api = ZitiManagementAPI(settings)
    client_api = ZitiClientAPI(settings)
    identity = await mgmt_api.search_identity(identity_name)
    if identity:
        raise ProxyIdentityAlreadyExistsError("A proxy identity with name `` already exists.")

    identity_id = await mgmt_api.create_device_identity(identity_name, tags=tags)
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
    )


def _get_enroll_token_claims(identity: dict[str, Any]):
    jwt_token = identity["data"]["enrollment"]["ott"]["jwt"]
    return jwt.decode(jwt_token, algorithms=["RS256"], options={"verify_signature": False})


def _generate_identity_json(
    ziti_api_url: str,
    pkey_pem: str,
    certificate_pem: str,
    ca_pem: str,
) -> dict[str, Any]:
    return {
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
