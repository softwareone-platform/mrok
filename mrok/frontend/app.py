from http import HTTPStatus
from pathlib import Path
from typing import Any

from httpcore import AsyncConnectionPool
from jinja2 import Environment, FileSystemLoader, select_autoescape

from mrok.conf import get_settings
from mrok.frontend.utils import get_target_name, parse_accept_header
from mrok.proxy.app import ProxyAppBase
from mrok.proxy.backend import AIOZitiNetworkBackend
from mrok.proxy.exceptions import InvalidTargetError
from mrok.types.proxy import ASGIReceive, ASGISend, Scope

ERROR_TEMPLATE_FORMATS = {
    "application/json": "json",
    "text/html": "html",
}


class FrontendProxyApp(ProxyAppBase):
    def __init__(
        self,
        identity_file: str,
        *,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        retries: int = 0,
    ):
        self._identity_file = identity_file
        self._jinja_env_cache: dict[Path, Environment] = {}
        self._templates_by_error = get_settings().frontend.get("errors", {})
        super().__init__(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            retries=retries,
        )

    def setup_connection_pool(
        self,
        max_connections: int | None,
        max_keepalive_connections: int | None,
        keepalive_expiry: float | None,
        retries: int,
    ) -> AsyncConnectionPool:
        return AsyncConnectionPool(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            retries=retries,
            network_backend=AIOZitiNetworkBackend(self._identity_file),
        )

    def get_upstream_base_url(self, scope: Scope) -> str:
        target = get_target_name(
            {k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", {})}
        )
        if not target:
            raise InvalidTargetError()

        return f"http://{target.lower()}"

    async def send_error_response(
        self,
        scope: Scope,
        send: ASGISend,
        http_status: int,
        body: str,
        headers: list[tuple[bytes, bytes]] | None = None,
    ):
        request_headers = {
            k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", {})
        }
        accept_header = request_headers.get("accept")
        if not (accept_header and str(http_status) in self._templates_by_error):
            return await super().send_error_response(scope, send, http_status, body)

        available_templates = self._templates_by_error[str(http_status)]

        media_types = parse_accept_header(accept_header)
        for media_type in media_types:
            template_format = ERROR_TEMPLATE_FORMATS.get(media_type)
            if template_format and template_format in available_templates:
                template_path = available_templates[template_format]
                rendered = await self._render_error_template(
                    Path(template_path), scope, http_status, body
                )
                return await super().send_error_response(
                    scope,
                    send,
                    http_status,
                    rendered,
                    headers=[(b"content-type", media_type.encode("latin-1"))],
                )

        return await super().send_error_response(scope, send, http_status, body)

    async def _render_error_template(
        self, template_path: Path, scope: Scope, http_status: int, body: str
    ) -> str:
        env = self._get_jinja_env(template_path)
        template = env.get_template(template_path.name)
        status_title = HTTPStatus(http_status).name.replace("_", " ").title()
        context = {
            "status": http_status,
            "status_title": status_title,
            "body": body,
            "request": self._extract_request_context(scope),
        }

        return await template.render_async(context)

    def _extract_request_context(self, scope: Scope) -> dict[str, Any]:
        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope.get("headers", [])}

        return {
            "method": scope.get("method"),
            "path": scope.get("path"),
            "raw_path": scope.get("raw_path", b"").decode("latin-1"),
            "query_string": scope.get("query_string", b"").decode("latin-1"),
            "scheme": scope.get("scheme"),
            "headers": headers,
            "client": scope.get("client"),
            "server": scope.get("server"),
            "http_version": scope.get("http_version"),
        }

    def _get_jinja_env(self, template_path: Path) -> Environment:
        template_dir = template_path.parent

        if template_dir not in self._jinja_env_cache:
            self._jinja_env_cache[template_dir] = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(
                    enabled_extensions=("html", "xml"),
                    default_for_string=False,
                ),
                enable_async=True,
            )

        return self._jinja_env_cache[template_dir]

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend) -> None:
        is_auth_enabled = get_settings().frontend.auth.enabled
        if is_auth_enabled and scope.get("type") == "http" and "auth_identity" not in scope:
            return await super().send_error_response(scope, send, 401, "Unauthenticated")
        return await super().__call__(scope, receive, send)
