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
    logger.info(f"Bootstrapping '{identity_name}' identity...")

    identity_json = None
    existing_identity = await mgmt_api.search_identity(identity_name)
    policy = await mgmt_api.search_router_policy(identity_name)
    config_type_name = f"{mode}.proxy.v1"
    config_type = await mgmt_api.search_config_type(config_type_name)

    if forced and existing_identity:
        logger.info(f"Deleting existing identity '{identity_name}' ({existing_identity['id']})")

        if policy:
            await mgmt_api.delete_router_policy(policy["id"])
            logger.info(f"Deleted existing ERP '{policy['name']}' ({policy['id']})")
            policy = None

        await mgmt_api.delete_identity(existing_identity["id"])
        logger.info("Deleted existing identity")
        existing_identity = None

    if forced and config_type:
        await mgmt_api.delete_config_type(config_type["id"])
        logger.info(f"Deleted existing config type '{config_type_name}' ({config_type['id']})")
        config_type = None

    if existing_identity:
        frontend_id = existing_identity["id"]
        logger.info(f"Identity '{identity_name}' ({frontend_id}) is already enrolled")
    else:
        frontend_id, identity_json = await enroll_proxy_identity(
            mgmt_api,
            client_api,
            identity_name,
            tags=tags,
        )
        logger.info(f"Identity '{identity_name}' ({frontend_id}) successfully enrolled")

    if not policy:
        policy_id = await mgmt_api.create_router_policy(
            identity_name,
            frontend_id,
            tags=tags,
        )
        logger.info(f"Created ERP '{identity_name}' ({policy_id})")
    else:
        logger.info(f"Found ERP '{policy['name']}' ({policy['id']})")

    if config_type is None:
        config_type_id = await mgmt_api.create_config_type(config_type_name, tags=tags)
        logger.info(f"Created '{config_type_name}' ({config_type_id}) config type")
    else:
        logger.info(f"Found '{config_type_name}' ({config_type['id']}) config type")

    if config_type and existing_identity:
        logger.info(f"Identity '{identity_name}' was already bootstrapped")
    else:
        logger.info("Bootstrap completed")

    return frontend_id, identity_json
