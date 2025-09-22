import logging
from typing import Any

from mrok.conf import Settings
from mrok.ziti.api import TagsType, ZitiManagementAPI
from mrok.ziti.errors import (
    ConfigTypeNotFoundError,
    ProxyIdentityNotFoundError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
)

logger = logging.getLogger(__name__)


async def register_service(
    settings: Settings, mgmt_api: ZitiManagementAPI, extension_id: str, tags: TagsType | None
) -> dict[str, Any]:
    extension_id = extension_id.lower()
    registered = False
    proxy_identity = await mgmt_api.search_identity(settings.proxy.identity)
    if not proxy_identity:
        raise ProxyIdentityNotFoundError(
            f"Identity for proxy `{settings.proxy.identity}` not found.",
        )

    config_type = await mgmt_api.search_config_type(f"{settings.proxy.mode}.proxy.v1")
    if not config_type:
        raise ConfigTypeNotFoundError(f"Config type `{settings.proxy.mode}.proxy.v1` not found.")

    config = await mgmt_api.search_config(extension_id)
    if not config:
        config_id = await mgmt_api.create_config(extension_id, config_type["id"], tags=tags)
        registered = True
    else:
        config_id = config["id"]
    service = await mgmt_api.search_service(extension_id)
    if not service:
        service_id = await mgmt_api.create_service(extension_id, config_id, tags=tags)
        service = await mgmt_api.get_service(service_id)
        registered = True
    else:
        service_id = service["id"]
    proxy_identity_id = proxy_identity["id"]
    service_policy_name = f"{extension_id}:{settings.proxy.identity}:dial"
    dial_service_policy = await mgmt_api.search_service_policy(service_policy_name)
    if not dial_service_policy:
        await mgmt_api.create_dial_service_policy(
            service_policy_name,
            service_id,
            proxy_identity_id,
            tags=tags,
        )
        registered = True

    router_policy = await mgmt_api.search_service_router_policy(extension_id)
    if not router_policy:
        await mgmt_api.create_service_router_policy(extension_id, service_id, tags=tags)
        registered = True
    if not registered:
        raise ServiceAlreadyRegisteredError(f"Extension `{extension_id}` already registered.")
    return service


async def unregister_service(
    settings: Settings, mgmt_api: ZitiManagementAPI, extension_id: str
) -> None:
    service = await mgmt_api.search_service(extension_id)
    if not service:
        raise ServiceNotFoundError(f"Extension `{extension_id}` not found.")

    router_policy = await mgmt_api.search_service_router_policy(extension_id)
    if router_policy:
        await mgmt_api.delete_service_router_policy(router_policy["id"])

    service_policy_name = f"{extension_id}:{settings.proxy.identity}:dial"

    dial_service_policy = await mgmt_api.search_service_policy(service_policy_name)
    if dial_service_policy:
        await mgmt_api.delete_service_policy(dial_service_policy["id"])

    config = await mgmt_api.search_config(extension_id)
    if config:
        await mgmt_api.delete_config(config["id"])

    await mgmt_api.delete_service(service["id"])


async def get_service(
    mgmt_api: ZitiManagementAPI, id_or_extension_id: str
) -> dict[str, Any] | None:
    return await mgmt_api.search_service(id_or_extension_id)
