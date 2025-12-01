import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Body, HTTPException, status

from mrok.controller.dependencies import AppSettings, ZitiClientAPI, ZitiManagementAPI
from mrok.controller.openapi import examples
from mrok.controller.pagination import LimitOffsetPage, paginate
from mrok.controller.schemas import ExtensionCreate, ExtensionRead, InstanceCreate, InstanceRead
from mrok.ziti.constants import MROK_SERVICE_TAG_NAME
from mrok.ziti.errors import (
    ConfigTypeNotFoundError,
    ProxyIdentityNotFoundError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
)
from mrok.ziti.identities import register_identity, unregister_identity
from mrok.ziti.services import register_service, unregister_service

logger = logging.getLogger("mrok.controller")

router = APIRouter()


async def fetch_extension_or_404(mgmt_api: ZitiManagementAPI, id_or_extension_id: str):
    service = await mgmt_api.search_service(id_or_extension_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return service


async def fetch_instance_or_404(
    mgmt_api: ZitiManagementAPI, id_or_extension_id: str, id_or_instance_id: str
):
    service = await fetch_extension_or_404(mgmt_api, id_or_extension_id)
    if id_or_instance_id.startswith("INS-"):
        id_or_name = f"{id_or_instance_id}.{service['name']}"
    else:
        id_or_name = id_or_instance_id
    identity = await mgmt_api.search_identity(id_or_name)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return identity


@router.post(
    "",
    response_model=ExtensionRead,
    responses={
        201: {
            "description": "Extension",
            "content": {
                "application/json": {
                    "example": examples.EXTENSION_RESPONSE,
                }
            },
        },
    },
    status_code=status.HTTP_201_CREATED,
    tags=["Extensions"],
)
async def create_extension(
    settings: AppSettings,
    mgmt_api: ZitiManagementAPI,
    data: Annotated[
        ExtensionCreate,
        Body(
            openapi_examples={
                "create_extension": {
                    "summary": "Create an Extension",
                    "description": ("Create a new Extension."),
                    "value": {
                        "extension": {"id": "EXT-1234-5678"},
                        "tags": {"account": "ACC-5555-3333"},
                    },
                }
            }
        ),
    ],
):
    try:
        service = await register_service(settings, mgmt_api, data.extension.id, data.tags)
        return ExtensionRead(
            id=service["id"],
            name=service["name"],
            tags=service["tags"],
        )
    except (ProxyIdentityNotFoundError, ConfigTypeNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OpenZiti not configured properly: {e}",
        ) from e
    except ServiceAlreadyRegisteredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{id_or_extension_id}",
    response_model=ExtensionRead,
    responses={
        200: {
            "description": "Extension",
            "content": {"application/json": {"example": examples.EXTENSION_RESPONSE}},
        },
    },
    dependencies=[],
    tags=["Extensions"],
)
async def get_extension_by_id_or_extension_id(
    mgmt_api: ZitiManagementAPI,
    id_or_extension_id: str,
    with_instances: Literal["none", "online", "offline"] = "none",
):
    extension = await fetch_extension_or_404(mgmt_api, id_or_extension_id)

    if with_instances == "none":
        return ExtensionRead(**extension)

    instances = list(
        filter(
            lambda ir: ir.status == with_instances,
            [
                InstanceRead(**identity)
                async for identity in mgmt_api.identities(
                    {"filter": f'tags.{MROK_SERVICE_TAG_NAME} = "{extension["name"]}"'}
                )
            ],
        )
    )

    return ExtensionRead(**extension, instances=instances)


@router.delete(
    "/{id_or_extension_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Extensions"],
)
async def delete_instance_by_id_or_extension_id(
    settings: AppSettings,
    mgmt_api: ZitiManagementAPI,
    id_or_extension_id: str,
):
    try:
        await unregister_service(settings, mgmt_api, id_or_extension_id)
    except ServiceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        )


@router.get(
    "",
    response_model=LimitOffsetPage[ExtensionRead],
    responses={
        200: {
            "description": "List of Extensions",
            "content": {
                "application/json": {
                    "example": {
                        "data": [examples.EXTENSION_RESPONSE],
                        "$meta": {
                            "pagination": {
                                "total": 1,
                                "limit": 10,
                                "offset": 0,
                            },
                        },
                    },
                },
            },
        },
    },
    tags=["Extensions"],
)
async def get_extensions(
    mgmt_api: ZitiManagementAPI,
):
    return await paginate(mgmt_api, "/services", ExtensionRead)


@router.post(
    "/{id_or_extension_id}/instances",
    response_model=InstanceRead,
    responses={
        201: {
            "description": "Instance",
            "content": {
                "application/json": {
                    "example": examples.INSTANCE_CREATE_RESPONSE,
                }
            },
        },
    },
    status_code=status.HTTP_201_CREATED,
    tags=["Instances"],
)
async def create_extension_instances(
    settings: AppSettings,
    mgmt_api: ZitiManagementAPI,
    client_api: ZitiClientAPI,
    id_or_extension_id: str,
    data: Annotated[
        InstanceCreate,
        Body(
            openapi_examples={
                "create_extension": {
                    "summary": "Create an Extension Instance",
                    "description": ("Create a new Instance of an Extension."),
                    "value": {
                        "instance": {"id": "INS-1234-5678-0001"},
                        "tags": {"account": "ACC-5555-3333"},
                    },
                }
            }
        ),
    ],
):
    service = await fetch_extension_or_404(mgmt_api, id_or_extension_id)
    identity, identity_file = await register_identity(
        settings, mgmt_api, client_api, service["name"], data.instance.id, data.tags
    )
    return InstanceRead(
        id=identity["id"],
        name=identity["name"],
        identity=identity_file,
        tags=identity["tags"],
    )


@router.get(
    "/{id_or_extension_id}/instances",
    response_model=LimitOffsetPage[InstanceRead],
    responses={
        200: {
            "description": "List of Instances.",
            "content": {
                "application/json": {
                    "example": {
                        "data": [examples.INSTANCE_RESPONSE],
                        "$meta": {
                            "pagination": {
                                "total": 1,
                                "limit": 10,
                                "offset": 0,
                            },
                        },
                    },
                },
            },
        },
    },
    dependencies=[],
    tags=["Instances"],
)
async def list_extension_instances(
    mgmt_api: ZitiManagementAPI,
    id_or_extension_id: str,
):
    service = await fetch_extension_or_404(mgmt_api, id_or_extension_id)
    return await paginate(
        mgmt_api,
        "/identities",
        InstanceRead,
        {"filter": f'tags.{MROK_SERVICE_TAG_NAME} = "{service["name"]}"'},
    )


@router.get(
    "/{id_or_extension_id}/instances/{id_or_instance_id}",
    response_model=InstanceRead,
    responses={
        200: {
            "description": "Instance",
            "content": {"application/json": {"example": examples.INSTANCE_RESPONSE}},
        },
    },
    dependencies=[],
    tags=["Instances"],
)
async def get_instance_by_id_or_instance_id(
    mgmt_api: ZitiManagementAPI,
    id_or_extension_id: str,
    id_or_instance_id: str,
):
    identity = await fetch_instance_or_404(mgmt_api, id_or_extension_id, id_or_instance_id)
    return InstanceRead(**identity)


@router.delete(
    "/{id_or_extension_id}/instances/{id_or_instance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Instances"],
)
async def delete_instance_by_id_or_instance_id(
    settings: AppSettings,
    mgmt_api: ZitiManagementAPI,
    id_or_extension_id: str,
    id_or_instance_id: str,
):
    identity = await fetch_instance_or_404(mgmt_api, id_or_extension_id, id_or_instance_id)
    instance_id, extension_id = identity["name"].split(".")
    await unregister_identity(settings, mgmt_api, extension_id, instance_id)
