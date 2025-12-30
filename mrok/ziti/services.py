import logging
from typing import Any

from mrok.conf import Settings
from mrok.types.ziti import Tags
from mrok.ziti.api import ZitiManagementAPI
from mrok.ziti.errors import (
    ConfigTypeNotFoundError,
    ProxyIdentityNotFoundError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
)

logger = logging.getLogger(__name__)


async def register_service(
    settings: Settings, mgmt_api: ZitiManagementAPI, external_id: str, tags: Tags | None
) -> dict[str, Any]:
    service_name = external_id.lower()
    registered = False
    proxy_identity = await mgmt_api.search_identity(settings.proxy.identity)
    if not proxy_identity:
        raise ProxyIdentityNotFoundError(
            f"Identity for proxy `{settings.proxy.identity}` not found.",
        )

    config_type = await mgmt_api.search_config_type(f"{settings.proxy.mode}.proxy.v1")
    if not config_type:
        raise ConfigTypeNotFoundError(f"Config type `{settings.proxy.mode}.proxy.v1` not found.")

    config = await mgmt_api.search_config(service_name)
    if not config:
        config_id = await mgmt_api.create_config(service_name, config_type["id"], tags=tags)
        registered = True
    else:
        config_id = config["id"]
    service = await mgmt_api.search_service(service_name)
    if not service:
        service_id = await mgmt_api.create_service(service_name, config_id, tags=tags)
        service = await mgmt_api.get_service(service_id)
        registered = True
    else:
        service_id = service["id"]
    proxy_identity_id = proxy_identity["id"]
    service_policy_name = f"{service_name}:{settings.proxy.identity}:dial"
    dial_service_policy = await mgmt_api.search_service_policy(service_policy_name)
    if not dial_service_policy:
        await mgmt_api.create_dial_service_policy(
            service_policy_name,
            service_id,
            proxy_identity_id,
            tags=tags,
        )
        registered = True

    router_policy = await mgmt_api.search_service_router_policy(service_name)
    if not router_policy:
        await mgmt_api.create_service_router_policy(service_name, service_id, tags=tags)
        registered = True
    if not registered:
        raise ServiceAlreadyRegisteredError(f"Service `{external_id}` already registered.")
    return service


async def unregister_service(
    settings: Settings, mgmt_api: ZitiManagementAPI, external_id: str
) -> None:
    service_name = external_id.lower()
    service = await mgmt_api.search_service(service_name)
    if not service:
        raise ServiceNotFoundError(f"Service `{external_id}` not found.")

    router_policy = await mgmt_api.search_service_router_policy(service_name)
    if router_policy:
        await mgmt_api.delete_service_router_policy(router_policy["id"])

    service_policy_name = f"{service_name}:{settings.proxy.identity}:dial"

    dial_service_policy = await mgmt_api.search_service_policy(service_policy_name)
    if dial_service_policy:
        await mgmt_api.delete_service_policy(dial_service_policy["id"])

    config = await mgmt_api.search_config(service_name)
    if config:
        await mgmt_api.delete_config(config["id"])

    await mgmt_api.delete_service(service["id"])
