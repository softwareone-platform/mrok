import abc
import asyncio
import logging

from mrok.http.types import ASGIReceive, ASGISend, Scope, StreamReader, StreamWriter

logger = logging.getLogger("mrok.proxy")


class BackendNotFoundError(Exception):
    pass


class ForwardAppBase(abc.ABC):
    """Generic HTTP forwarder base class.

    Subclasses must implement `select_backend(scope)` to return an
    (asyncio.StreamReader, asyncio.StreamWriter) pair connected to the
    desired backend. The base class implements the HTTP/1.1 framing
    and streaming logic (requests and responses).
    """

    def __init__(
        self,
        read_chunk_size: int = 65536,
        lifespan_timeout: float = 10.0,
    ) -> None:
        self._read_chunk_size: int = int(read_chunk_size)
        self._lifespan_timeout = lifespan_timeout

    async def handle_lifespan(self, receive: ASGIReceive, send: ASGISend) -> None:
        while True:
            event = await receive()
            etype = event.get("type")

            if etype == "lifespan.startup":
                try:
                    await asyncio.wait_for(self.startup(), self._lifespan_timeout)
                except TimeoutError:
                    logger.exception("Lifespan startup timed out")
                    await send({"type": "lifespan.startup.failed", "message": "startup timeout"})
                    continue
                except Exception as e:
                    logger.exception("Exception during lifespan startup")
                    await send({"type": "lifespan.startup.failed", "message": str(e)})
                    continue
                await send({"type": "lifespan.startup.complete"})

            elif etype == "lifespan.shutdown":
                try:
                    await asyncio.wait_for(self.shutdown(), self._lifespan_timeout)
                except TimeoutError:
                    logger.exception("Lifespan shutdown timed out")
                    await send({"type": "lifespan.shutdown.failed", "message": "shutdown timeout"})
                    return
                except Exception as exc:
                    logger.exception("Exception during lifespan shutdown")
                    await send({"type": "lifespan.shutdown.failed", "message": str(exc)})
                    return
                await send({"type": "lifespan.shutdown.complete"})
                return

    @abc.abstractmethod
    async def select_backend(
        self,
        scope: Scope,
        headers: dict[str, str],
    ) -> tuple[StreamReader, StreamWriter] | tuple[None, None]:
        """Return (reader, writer) connected to the target backend."""

    async def startup(self):
        return

    async def shutdown(self):
        return

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend) -> None:
        """ASGI callable entry point.

        Delegates to smaller helper methods for readability. Subclasses only
        need to implement backend selection.
        """
        scope_type = scope.get("type")
        if scope_type == "lifespan":
            await self.handle_lifespan(receive, send)
            return

        if scope.get("type") != "http":
            await send({"type": "http.response.start", "status": 500, "headers": []})
            await send({"type": "http.response.body", "body": b"Unsupported"})
            return

        method = scope.get("method", "GET")
        path_qs = self.format_path(scope)

        headers = list(scope.get("headers", []))
        headers = self.ensure_host_header(headers, scope)
        reader, writer = await self.select_backend(
            scope, {k[0].decode().lower(): k[1].decode() for k in headers}
        )

        if not (reader and writer):
            await send({"type": "http.response.start", "status": 502, "headers": []})
            await send({"type": "http.response.body", "body": b"Bad Gateway"})
            return

        use_chunked = self.ensure_chunked_if_needed(headers)

        await self.write_request_line_and_headers(writer, method, path_qs, headers)

        await self.stream_request_body(receive, writer, use_chunked)

        status_line = await reader.readline()
        if not status_line:
            await send({"type": "http.response.start", "status": 502, "headers": []})
            await send({"type": "http.response.body", "body": b"Bad Gateway"})
            writer.close()
            await writer.wait_closed()
            return

        status, headers_out, raw_headers = await self.read_status_and_headers(reader, status_line)

        await send({"type": "http.response.start", "status": status, "headers": headers_out})

        await self.stream_response_body(reader, send, raw_headers)

        writer.close()
        await writer.wait_closed()

    def format_path(self, scope: Scope) -> str:
        raw_path = scope.get("raw_path")
        if raw_path:
            return raw_path.decode()
        q = scope.get("query_string", b"")
        path = scope.get("path", "/")
        path_qs = path
        if q:
            path_qs += "?" + q.decode()
        return path_qs

    def ensure_host_header(
        self, headers: list[tuple[bytes, bytes]], scope: Scope
    ) -> list[tuple[bytes, bytes]]:
        if any(n.lower() == b"host" for n, _ in headers):
            return headers
        server = scope.get("server")
        if server:
            host = f"{server[0]}:{server[1]}" if server[1] else server[0]
            headers.append((b"host", host.encode()))
        return headers

    def ensure_chunked_if_needed(self, headers: list[tuple[bytes, bytes]]) -> bool:
        has_content_length = any(n.lower() == b"content-length" for n, _ in headers)
        has_transfer_encoding = any(n.lower() == b"transfer-encoding" for n, _ in headers)
        if not has_content_length and not has_transfer_encoding:
            headers.append((b"transfer-encoding", b"chunked"))
            return True
        return False

    async def write_request_line_and_headers(
        self,
        writer: StreamWriter,
        method: str,
        path_qs: str,
        headers: list[tuple[bytes, bytes]],
    ) -> None:
        writer.write(f"{method} {path_qs} HTTP/1.1\r\n".encode())
        for name, value in headers:
            if name.lower() == b"expect":
                continue
            writer.write(name + b": " + value + b"\r\n")
        writer.write(b"\r\n")
        await writer.drain()

    async def stream_request_body(
        self, receive: ASGIReceive, writer: StreamWriter, use_chunked: bool
    ) -> None:
        if use_chunked:
            await self.stream_request_chunked(receive, writer)
            return

        await self.stream_request_until_end(receive, writer)

    async def stream_request_chunked(self, receive: ASGIReceive, writer: StreamWriter) -> None:
        """Send request body to backend using HTTP/1.1 chunked encoding."""
        while True:
            event = await receive()
            if event["type"] == "http.request":
                body = event.get("body", b"") or b""
                if body:
                    writer.write(f"{len(body):X}\r\n".encode())
                    writer.write(body)
                    writer.write(b"\r\n")
                    await writer.drain()
                if not event.get("more_body", False):
                    break
            elif event["type"] == "http.disconnect":
                writer.close()
                return

        writer.write(b"0\r\n\r\n")
        await writer.drain()

    async def stream_request_until_end(self, receive: ASGIReceive, writer: StreamWriter) -> None:
        """Send request body to backend when content length/transfer-encoding
        already provided (no chunking).
        """
        while True:
            event = await receive()
            if event["type"] == "http.request":
                body = event.get("body", b"") or b""
                if body:
                    writer.write(body)
                    await writer.drain()
                if not event.get("more_body", False):
                    break
            elif event["type"] == "http.disconnect":
                writer.close()
                return

    async def read_status_and_headers(
        self, reader: StreamReader, first_line: bytes
    ) -> tuple[int, list[tuple[bytes, bytes]], dict[bytes, bytes]]:
        parts = first_line.decode(errors="ignore").split(" ", 2)
        status = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 502
        headers: list[tuple[bytes, bytes]] = []
        raw_headers: dict[bytes, bytes] = {}
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break
            i = line.find(b":")
            if i == -1:
                continue
            name = line[:i].strip().lower()
            value = line[i + 1 :].strip()
            headers.append((name, value))
            raw_headers[name] = value

        return status, headers, raw_headers

    def is_chunked(self, te_value: bytes) -> bool:
        """Return True if transfer-encoding header tokens include 'chunked'."""
        if not te_value:
            return False
        # split on commas, strip spaces and check tokens
        tokens = [t.strip() for t in te_value.split(b",")]
        return any(t.lower() == b"chunked" for t in tokens)

    def parse_content_length(self, cl_value: bytes | None) -> int | None:
        """Parse Content-Length header value to int, or return None if invalid."""
        if cl_value is None:
            return None
        try:
            return int(cl_value)
        except Exception:
            return None

    async def drain_trailers(self, reader: StreamReader) -> None:
        """Consume trailer header lines until an empty line is encountered."""
        while True:
            trailer = await reader.readline()
            if trailer in (b"\r\n", b"\n", b""):
                break

    async def stream_response_chunked(self, reader: StreamReader, send: ASGISend) -> None:
        """Read chunked-encoded response from reader, decode and forward to ASGI send."""
        while True:
            size_line = await reader.readline()
            if not size_line:
                break
            size_str = size_line.split(b";", 1)[0].strip()
            try:
                size = int(size_str, 16)
            except Exception:
                break
            if size == 0:
                # consume trailers
                await self.drain_trailers(reader)
                break
            try:
                chunk = await reader.readexactly(size)
            except Exception:
                break
            # consume the CRLF after the chunk
            try:
                await reader.readexactly(2)
            except Exception:
                logger.warning("failed to read CRLF after chunk from backend")
            await send({"type": "http.response.body", "body": chunk, "more_body": True})

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def stream_response_with_content_length(
        self, reader: StreamReader, send: ASGISend, content_length: int
    ) -> None:
        """Read exactly content_length bytes and forward to ASGI send events."""
        remaining = content_length
        sent_final = False
        while remaining > 0:
            to_read = min(self._read_chunk_size, remaining)
            chunk = await reader.read(to_read)
            if not chunk:
                break
            remaining -= len(chunk)
            more = remaining > 0
            await send({"type": "http.response.body", "body": chunk, "more_body": more})
            if not more:
                sent_final = True

        if not sent_final:
            await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def stream_response_until_eof(self, reader: StreamReader, send: ASGISend) -> None:
        """Read from reader until EOF and forward chunks to ASGI send events."""
        while True:
            chunk = await reader.read(self._read_chunk_size)
            if not chunk:
                break
            await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def stream_response_body(
        self, reader: StreamReader, send: ASGISend, raw_headers: dict[bytes, bytes]
    ) -> None:
        te = raw_headers.get(b"transfer-encoding", b"").lower()
        cl = raw_headers.get(b"content-length")

        if self.is_chunked(te):
            await self.stream_response_chunked(reader, send)
            return

        content_length = self.parse_content_length(cl)
        if content_length is not None:
            await self.stream_response_with_content_length(reader, send, content_length)
            return

        await self.stream_response_until_eof(reader, send)
