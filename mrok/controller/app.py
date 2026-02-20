import logging
from functools import partial

import fastapi_pagination
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute, APIRouter

from mrok.authentication.manager import HTTPAuthManager
from mrok.conf import Settings, get_settings
from mrok.controller.fastapi_auth_adapter import build_fastapi_auth_dependencies
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


def setup_app(settings: Settings):
    auth_manager = HTTPAuthManager(settings.controller.auth)
    auth_dependency = build_fastapi_auth_dependencies(auth_manager)
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

    @app.get("/healthcheck")
    async def healthcheck():
        return {"status": "healthy"}

    app.include_router(
        extensions_router,
        prefix="/extensions",
        dependencies=[Depends(auth_dependency)],
    )
    app.include_router(
        instances_router,
        prefix="/instances",
        dependencies=[Depends(auth_dependency)],
    )

    app.openapi = partial(generate_openapi_spec, app, settings)  # type: ignore[method-assign]
    return app


app = setup_app(get_settings())
