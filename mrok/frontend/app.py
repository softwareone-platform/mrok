import re

from httpcore import AsyncConnectionPool

from mrok.conf import get_settings
from mrok.proxy.app import ProxyAppBase
from mrok.proxy.backend import AIOZitiNetworkBackend
from mrok.proxy.exceptions import InvalidTargetError
from mrok.proxy.types import Scope

RE_SUBDOMAIN = re.compile(r"(?i)^(?:EXT-\d{4}-\d{4}|INS-\d{4}-\d{4}-\d{4})$")


class FrontendProxyApp(ProxyAppBase):
    def __init__(
        self,
        identity_file: str,
        *,
        max_connections: int = 1000,
        max_keepalive_connections: int = 10,
        keepalive_expiry: float = 120.0,
        retries=0,
    ):
        self._identity_file = identity_file
        self._proxy_domain = self._get_proxy_domain()
        super().__init__(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            retries=retries,
        )

    def setup_connection_pool(
        self,
        max_connections: int | None = 1000,
        max_keepalive_connections: int | None = 100,
        keepalive_expiry: float | None = 120.0,
        retries: int = 0,
    ) -> AsyncConnectionPool:
        return AsyncConnectionPool(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            retries=retries,
            network_backend=AIOZitiNetworkBackend(self._identity_file),
        )

    def get_upstream_base_url(self, scope: Scope) -> str:
        target = self._get_target_name(
            {k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", {})}
        )
        return f"http://{target.lower()}"

    def _get_proxy_domain(self):
        settings = get_settings()
        return (
            settings.proxy.domain
            if settings.proxy.domain[0] == "."
            else f".{settings.proxy.domain}"
        )

    def _get_target_from_header(self, headers: dict[str, str], name: str) -> str | None:
        header_value = headers.get(name, "")
        if self._proxy_domain in header_value:
            if ":" in header_value:
                header_value, _ = header_value.split(":", 1)
            return header_value[: -len(self._proxy_domain)]

    def _get_target_name(self, headers: dict[str, str]) -> str:
        target = self._get_target_from_header(headers, "x-forwarded-host")
        if not target:
            target = self._get_target_from_header(headers, "host")
        if not target or not RE_SUBDOMAIN.fullmatch(target):
            raise InvalidTargetError()
        return target
