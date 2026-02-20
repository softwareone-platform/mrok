from dynaconf.utils.boxing import DynaBox
from starlette.datastructures import Headers

from mrok.authentication.base import AuthIdentity, BaseHTTPAuthBackend
from mrok.authentication.registry import get_authentication_backend


class HTTPAuthManager:
    def __init__(self, auth_settings: DynaBox):
        self.auth_settings = auth_settings
        self.active_backends: list[BaseHTTPAuthBackend] = []
        self._setup_backends()

    def _setup_backends(self):
        enabled_keys = self.auth_settings.get("backends", [])

        for key in enabled_keys:
            backend_cls = get_authentication_backend(key)
            if not backend_cls:
                raise ValueError(f"Backend '{key}' is not registered.")

            specific_config = self.auth_settings.get(key, {})
            self.active_backends.append(backend_cls(specific_config))

    async def authenticate(self, authorization: str | None) -> AuthIdentity | None:
        for backend in self.active_backends:
            identity = await backend.authenticate(authorization)
            if identity:
                return identity
        return None

    async def __call__(self, scope) -> AuthIdentity | None:
        headers = Headers(scope=scope)
        raw_authorization = headers.get("authorization")
        return await self.authenticate(raw_authorization)
