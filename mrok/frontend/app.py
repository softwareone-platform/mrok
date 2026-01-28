import re
from http import HTTPStatus
from pathlib import Path
from typing import Any

from httpcore import AsyncConnectionPool
from jinja2 import Environment, FileSystemLoader, select_autoescape

from mrok.conf import get_settings
from mrok.frontend.utils import parse_accept_header
from mrok.proxy.app import ProxyAppBase
from mrok.proxy.backend import AIOZitiNetworkBackend
from mrok.proxy.exceptions import InvalidTargetError
from mrok.types.proxy import ASGISend, Scope

RE_SUBDOMAIN = re.compile(r"(?i)^(?:EXT-\d{4}-\d{4}|INS-\d{4}-\d{4}-\d{4})$")

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
        retries=0,
    ):
        self._identity_file = identity_file
        self._settings = get_settings()
        self._proxy_domain = self._get_proxy_domain()
        self._jinja_env_cache: dict[Path, Environment] = {}
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
        target = self._get_target_name(
            {k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", {})}
        )
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
        errors = self._settings.frontend.get("errors", {})
        if not (accept_header and str(http_status) in errors):
            return await super().send_error_response(scope, send, http_status, body)

        available_templates = errors[str(http_status)]

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

    def _get_proxy_domain(self):
        return (
            self._settings.frontend.domain
            if self._settings.frontend.domain[0] == "."
            else f".{self._settings.frontend.domain}"
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
