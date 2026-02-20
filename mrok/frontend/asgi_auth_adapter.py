from mrok.authentication.manager import HTTPAuthManager


class ASGIAuthenticationMiddleware:
    def __init__(self, app, auth_manager: HTTPAuthManager, *, exclude_paths=None):
        self.app = app
        self.auth_manager = auth_manager
        self.exclude_paths = set(exclude_paths or [])

    async def __call__(self, scope, receive, send):
        authenticated = await self.auth_manager.authenticate(scope)
        if authenticated:
            scope["auth_identity"] = authenticated
        return await self.app(scope, receive, send)
