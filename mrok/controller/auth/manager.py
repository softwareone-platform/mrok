from dynaconf.utils.boxing import DynaBox
from fastapi import Request

from mrok.controller.auth.base import UNAUTHORIZED_EXCEPTION, AuthIdentity, BaseHTTPAuthBackend
from mrok.controller.auth.registry import get_authentication_backend


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

    async def __call__(self, request: Request) -> AuthIdentity:
        for backend in self.active_backends:
            identity = await backend(request)
            if identity:
                return identity

        raise UNAUTHORIZED_EXCEPTION
