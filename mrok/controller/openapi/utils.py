from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from mrok.conf import Settings


def generate_openapi_spec(app: FastAPI, settings: Settings):
    if app.openapi_schema:  # pragma: no cover
        return app.openapi_schema

    # for api_route in app.routes:
    #     if isinstance(api_route, APIRoute):
    #         for dep in api_route.dependant.dependencies:
    #             if dep.call and isinstance(dep.call, RQLQuery):
    #                 api_route.description = (
    #                     f"{api_route.description}\n\n"
    #                     "## Available RQL filters\n\n"
    #                     f"{dep.call.rules.get_documentation()}"
    #                 )

    spec = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        tags=app.openapi_tags,
        routes=app.routes,
    )
    # spec = inject_code_samples(
    #     spec,
    #     SnippetRenderer(),
    #     settings.api_base_url,
    # )
    app.openapi_schema = spec
    return app.openapi_schema
