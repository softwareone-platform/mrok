import asyncio
import logging
import time

from mrok.proxy.constants import MAX_REQUEST_BODY_BYTES, MAX_RESPONSE_BODY_BYTES
from mrok.proxy.metrics import MetricsCollector
from mrok.proxy.models import FixedSizeByteBuffer, HTTPHeaders, HTTPRequest, HTTPResponse
from mrok.proxy.utils import must_capture_request, must_capture_response
from mrok.types.proxy import (
    ASGIApp,
    ASGIReceive,
    ASGISend,
    Message,
    ResponseCompleteCallback,
    Scope,
)

logger = logging.getLogger("mrok.proxy")


class CaptureMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        on_response_complete: ResponseCompleteCallback,
    ):
        self.app = app
        self._on_response_complete = on_response_complete

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        method = scope["method"]
        path = scope["path"]
        query_string = scope.get("query_string", b"")
        req_headers_raw = scope.get("headers", [])
        req_headers = HTTPHeaders.from_asgi(req_headers_raw)

        state = {}

        req_buf = FixedSizeByteBuffer(MAX_REQUEST_BODY_BYTES)
        capture_req_body = must_capture_request(method, req_headers)

        request = HTTPRequest(
            method=method,
            url=path,
            headers=req_headers,
            query_string=query_string,
            start_time=start_time,
        )

        # Response capture
        resp_buf = FixedSizeByteBuffer(MAX_RESPONSE_BODY_BYTES)

        async def receive_wrapper() -> Message:
            msg = await receive()
            if capture_req_body and msg["type"] == "http.request":
                body = msg.get("body", b"")
                req_buf.write(body)
            return msg

        async def send_wrapper(msg: Message):
            if msg["type"] == "http.response.start":
                state["status"] = msg["status"]
                resp_headers = HTTPHeaders.from_asgi(msg.get("headers", []))
                state["resp_headers_raw"] = resp_headers

                state["capture_resp_body"] = must_capture_response(resp_headers)

            if state["capture_resp_body"] and msg["type"] == "http.response.body":
                body = msg.get("body", b"")
                resp_buf.write(body)

            await send(msg)

        await self.app(scope, receive_wrapper, send_wrapper)

        # Finalise request
        request.body = req_buf.getvalue() if capture_req_body else None
        request.body_truncated = req_buf.overflow if capture_req_body else None

        # Finalise response
        end_time = time.time()
        duration = end_time - start_time

        response = HTTPResponse(
            request=request,
            status=state["status"] or 0,
            headers=state["resp_headers_raw"],
            duration=duration,
            body=resp_buf.getvalue() if state["capture_resp_body"] else None,
            body_truncated=resp_buf.overflow if state["capture_resp_body"] else None,
        )
        asyncio.create_task(self._on_response_complete(response))


class MetricsMiddleware:
    def __init__(self, app: ASGIApp, metrics: MetricsCollector):
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start_time = await self.metrics.on_request_start(scope)
        status_code = 500

        async def wrapped_receive():
            msg = await receive()
            if msg["type"] == "http.request" and msg.get("body"):  # pragma: no branch
                await self.metrics.on_request_body(len(msg["body"]))
            return msg

        async def wrapped_send(msg):
            nonlocal status_code

            if msg["type"] == "http.response.start":
                status_code = msg["status"]
                await self.metrics.on_response_start(status_code)

            elif msg["type"] == "http.response.body":  # pragma: no branch
                body = msg.get("body", b"")
                await self.metrics.on_response_chunk(len(body))

            return await send(msg)

        try:
            await self.app(scope, wrapped_receive, wrapped_send)
        finally:
            await self.metrics.on_request_end(start_time, status_code)
