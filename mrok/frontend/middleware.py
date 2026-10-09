import json

from mrok.authentication import HTTPAuthManager
from mrok.frontend.utils import get_headers, get_target_name
from mrok.logging import request_target
from mrok.types.proxy import ASGIApp, ASGIReceive, ASGISend, Scope


class TargetMiddleware:
    """Expose the target (extension/instance) of the current request to the logging filters."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend):
        target = get_target_name(get_headers(scope))
        token = request_target.set(target)
        try:
            await self.app(scope, receive, send)
        finally:
            request_target.reset(token)


class HealthCheckMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend):
        if scope["type"] == "http" and scope["path"] == "/healthcheck":
            target = get_target_name(get_headers(scope))

            if not target:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [
                            [b"content-type", b"application/json"],
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": json.dumps({"status": "healthy"}).encode("utf-8"),
                    }
                )
                return

        await self.app(scope, receive, send)


class ASGIAuthenticationMiddleware:
    def __init__(self, app, auth_manager: HTTPAuthManager):
        self.app = app
        self.auth_manager = auth_manager

    async def __call__(self, scope, receive, send):
        identity = await self.auth_manager(scope)
        if identity:
            scope["identity"] = identity
        return await self.app(scope, receive, send)
