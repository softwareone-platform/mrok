import abc
import logging

from httpcore import AsyncConnectionPool, Request

from mrok.proxy.exceptions import ProxyError
from mrok.proxy.stream import ASGIRequestBodyStream
from mrok.types.proxy import ASGIReceive, ASGISend, Scope

logger = logging.getLogger("mrok.proxy")


HOP_BY_HOP_HEADERS = [
    b"connection",
    b"keep-alive",
    b"proxy-authenticate",
    b"proxy-authorization",
    b"te",
    b"trailers",
    b"transfer-encoding",
    b"upgrade",
]


class ProxyAppBase(abc.ABC):
    def __init__(
        self,
        *,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        retries: int = 0,
    ) -> None:
        self._pool = self.setup_connection_pool(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            retries=retries,
        )

    @abc.abstractmethod
    def setup_connection_pool(
        self,
        max_connections: int | None,
        max_keepalive_connections: int | None,
        keepalive_expiry: float | None,
        retries: int,
    ) -> AsyncConnectionPool:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_upstream_base_url(self, scope: Scope) -> str:
        raise NotImplementedError()

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend) -> None:
        if scope.get("type") == "lifespan":
            return

        if scope.get("type") != "http":
            await self._send_error(send, 500, "Unsupported")
            return

        try:
            base_url = self.get_upstream_base_url(scope)
            if base_url.endswith("/"):  # pragma: no cover
                base_url = base_url[:-1]
            full_path = self._format_path(scope)
            url = f"{base_url}{full_path}"
            method = scope.get("method", "GET").encode()
            headers = self._prepare_headers(scope)

            body_stream = ASGIRequestBodyStream(receive)

            request = Request(
                method=method,
                url=url,
                headers=headers,
                content=body_stream,
            )
            response = await self._pool.handle_async_request(request)
            logger.debug(f"connection pool status: {self._pool}")
            response_headers = []
            for k, v in response.headers:
                if k.lower() not in HOP_BY_HOP_HEADERS:
                    response_headers.append((k, v))

            await send(
                {
                    "type": "http.response.start",
                    "status": response.status,
                    "headers": response_headers,
                }
            )

            async for chunk in response.stream:  # type: ignore[union-attr]
                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    }
                )

            await send({"type": "http.response.body", "body": b"", "more_body": False})
            await response.aclose()

        except ProxyError as pe:
            await self._send_error(send, pe.http_status, pe.message)

        except Exception:
            logger.exception("Unexpected error in forwarder")
            await self._send_error(send, 502, "Bad Gateway")

    async def _send_error(self, send: ASGISend, http_status: int, body: str):
        try:
            await send({"type": "http.response.start", "status": http_status, "headers": []})
            await send({"type": "http.response.body", "body": body.encode()})
        except Exception as e:  # pragma: no cover
            logger.error(f"Cannot send error response: {e}")

    def _prepare_headers(self, scope: Scope) -> list[tuple[bytes, bytes]]:
        headers: list[tuple[bytes, bytes]] = []
        scope_headers = scope.get("headers", [])

        for k, v in scope_headers:
            if k.lower() not in HOP_BY_HOP_HEADERS:
                headers.append((k, v))

        self._merge_x_forwarded(headers, scope)

        return headers

    def _find_header(self, headers: list[tuple[bytes, bytes]], name: bytes) -> int | None:
        """Return index of header `name` in `headers`, or None if missing."""
        lname = name.lower()
        for i, (k, _) in enumerate(headers):
            if k.lower() == lname:
                return i
        return None

    def _merge_x_forwarded(self, headers: list[tuple[bytes, bytes]], scope: Scope) -> None:
        client = scope.get("client")
        if client:
            client_ip = client[0].encode()
            idx = self._find_header(headers, b"x-forwarded-for")
            if idx is None:
                headers.append((b"x-forwarded-for", client_ip))
            else:
                k, v = headers[idx]
                headers[idx] = (k, v + b", " + client_ip)

        server = scope.get("server")
        if server:
            if self._find_header(headers, b"x-forwarded-host") is None:
                headers.append((b"x-forwarded-host", server[0].encode()))
            if server[1] and self._find_header(headers, b"x-forwarded-port") is None:
                headers.append((b"x-forwarded-port", str(server[1]).encode()))

        # Always set the protocol to https for upstream
        idx_proto = self._find_header(headers, b"x-forwarded-proto")
        if idx_proto is None:
            headers.append((b"x-forwarded-proto", b"https"))
        else:
            k, _ = headers[idx_proto]
            headers[idx_proto] = (k, b"https")

    def _format_path(self, scope: Scope) -> str:
        raw_path = scope.get("raw_path")
        if raw_path:
            return raw_path.decode()
        q = scope.get("query_string", b"")
        path = scope.get("path", "/")
        path_qs = path
        if q:
            path_qs += "?" + q.decode()
        return path_qs
