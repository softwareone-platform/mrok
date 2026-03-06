import logging
from typing import Any

from mrok.types.ziti import Tags
from mrok.ziti.api import ZitiClientAPI, ZitiManagementAPI
from mrok.ziti.identities import enroll_proxy_identity

logger = logging.getLogger(__name__)


async def bootstrap_identity(
    mgmt_api: ZitiManagementAPI,
    client_api: ZitiClientAPI,
    identity_name: str,
    mode: str,
    forced: bool,
    tags: Tags | None,
) -> tuple[str, dict[str, Any] | None]:
    identity_json = None
    existing_identity = await mgmt_api.search_identity(identity_name)
    policy = await mgmt_api.search_router_policy(identity_name)
    config_type_name = f"{mode}.proxy.v1"
    config_type = await mgmt_api.search_config_type(config_type_name)

    if forced and existing_identity:
        if policy:
            await mgmt_api.delete_router_policy(policy["id"])
            policy = None

        await mgmt_api.delete_identity(existing_identity["id"])
        existing_identity = None

    if existing_identity:
        frontend_id = existing_identity["id"]
    else:
        frontend_id, identity_json = await enroll_proxy_identity(
            mgmt_api,
            client_api,
            identity_name,
            tags=tags,
        )

    if not policy:
        await mgmt_api.create_router_policy(
            identity_name,
            frontend_id,
            tags=tags,
        )

    if config_type is None:
        await mgmt_api.create_config_type(config_type_name, tags=tags)

    return frontend_id, identity_json
