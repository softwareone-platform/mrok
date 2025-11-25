import logging
from functools import partial

import fastapi_pagination
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute, APIRouter

from mrok.conf import get_settings
from mrok.controller.auth import authenticate
from mrok.controller.openapi import generate_openapi_spec
from mrok.controller.routes.extensions import router as extensions_router
from mrok.controller.routes.instances import router as instances_router

logger = logging.getLogger(__name__)


tags_metadata = [
    {
        "name": "Extensions",
        "description": "Manage Extensions (services).",
    },
    {
        "name": "Instances",
        "description": "Manage Extension Instances (identities).",
    },
]


def setup_custom_serialization(router: APIRouter):
    for api_route in router.routes:
        if (
            isinstance(api_route, APIRoute)
            and hasattr(api_route, "response_model")
            and api_route.response_model
        ):
            api_route.response_model_exclude_none = True


def setup_app():
    app = FastAPI(
        title="mrok Controller API",
        description="API to orchestrate OpenZiti for Extensions.",
        swagger_ui_parameters={"showExtensions": False, "showCommonExtensions": False},
        openapi_tags=tags_metadata,
        version="5.0.0",
        root_path="/public/v1",
    )
    fastapi_pagination.add_pagination(app)

    setup_custom_serialization(extensions_router)

    # TODO: Add healthcheck
    app.include_router(
        extensions_router,
        prefix="/extensions",
        dependencies=[Depends(authenticate)],
    )
    app.include_router(
        instances_router,
        prefix="/instances",
        dependencies=[Depends(authenticate)],
    )

    settings = get_settings()

    app.openapi = partial(generate_openapi_spec, app, settings)
    return app


app = setup_app()
