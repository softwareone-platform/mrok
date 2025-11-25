import logging

from fastapi import APIRouter, HTTPException, status

from mrok.controller.dependencies import ZitiManagementAPI
from mrok.controller.openapi import examples
from mrok.controller.pagination import LimitOffsetPage, paginate
from mrok.controller.schemas import InstanceRead
from mrok.ziti.constants import MROK_IDENTITY_TYPE_TAG_NAME, MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE

logger = logging.getLogger("mrok.controller")

router = APIRouter()


async def fetch_instance_or_404(mgmt_api: ZitiManagementAPI, id_or_instance_id: str):
    identity = await mgmt_api.search_identity(id_or_instance_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return identity


@router.get(
    "/{id_or_instance_id}",
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
    id_or_instance_id: str,
):
    identity = await fetch_instance_or_404(mgmt_api, id_or_instance_id)
    return InstanceRead(**identity)


@router.get(
    "",
    response_model=LimitOffsetPage[InstanceRead],
    responses={
        200: {
            "description": "List of Instances",
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
    tags=["Instances"],
)
async def get_instances(
    mgmt_api: ZitiManagementAPI,
):
    params = {
        "filter": f'tags.{MROK_IDENTITY_TYPE_TAG_NAME}="{MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE}"'
    }
    return await paginate(mgmt_api, "/identities", InstanceRead, extra_params=params)
