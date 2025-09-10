import logging
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, status

from mrok.controller.openapi import examples
from mrok.controller.pagination import LimitOffsetPage
from mrok.controller.schemas import ExtensionCreate, ExtensionRead, InstanceCreate, InstanceRead
from mrok.ziti.errors import (
    ConfigTypeNotFoundError,
    ProxyIdentityNotFoundError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
)
from mrok.ziti.services import get_service, register_service, unregister_service

logger = logging.getLogger("mrok.controller")

router = APIRouter()

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
    dependencies=[],
    tags=["Extensions"],
)
async def create_extension(
    data: Annotated[
        ExtensionCreate,
        Body(
            openapi_examples={
                "create_extension": {
                    "summary": "Create an Extension",
                    "description": ("Create a new Extension."),
                    "value": {
                        "extension": {"id": "EXT-1234-5678"},
                        "tags": {
                            "account": "ACC-5555-3333"
                        }
                    },
                }
            }
        ),
    ],
):
    try:
        service = await register_service(data.extension.id, data.tags)
        logger.info(f"service: {service}")
        return ExtensionRead(
            id=service["id"],
            name=service["name"],
            tags=service["tags"],
        )
    except (ProxyIdentityNotFoundError, ConfigTypeNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OpenZiti not configured properly: {e}.",
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
    id_or_extension_id: str,
):
    service = await get_service(id_or_extension_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return ExtensionRead(**service)


@router.delete(
    "/{id_or_extension_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Extensions"],
)
async def delete_instance_by_id_or_extension_id(
    id_or_extension_id: str,
):
    try:
        await unregister_service(id_or_extension_id)
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
    dependencies=[],
    tags=["Extensions"],
)
async def get_extensions():
    pass


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
                        "tags": {
                            "account": "ACC-5555-3333"
                        }
                    },
                }
            }
        ),
    ],
):
    pass


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
    id_or_extension_id: str,
):
    pass


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
    id_or_extension_id: str,
    id_or_instance_id: str,
):
    pass

@router.delete(
    "/{id_or_extension_id}/instances/{id_or_instance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Instances"],
)
async def delete_instance_by_id_or_instance_id(
    id_or_extension_id: str,
    id_or_instance_id: str,
):
    pass
