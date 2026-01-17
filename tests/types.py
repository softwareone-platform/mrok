from collections.abc import Awaitable, Callable, Iterable
from pathlib import PurePath
from typing import Any, Protocol

import zmq
from textual.app import App
from textual.pilot import Pilot

from mrok.conf import Settings
from mrok.types.proxy import ASGIReceive, ASGISend, Message

ZMQPublisher = tuple[zmq.Socket, int]


class SnapCompare(Protocol):
    def __call__(
        self,
        app: str | PurePath | App,
        press: Iterable[str] = (),
        terminal_size: tuple[int, int] = (80, 24),
        run_before: Callable[[Pilot], Awaitable[None] | None] | None = None,
    ) -> bool: ...


SettingsFactory = Callable[..., Settings]


class ReceiveFactory(Protocol):
    def __call__(self, messages: list[Message] | None = None) -> ASGIReceive: ...


SendFactory = Callable[[list[Message]], ASGISend]


class StatusEventFactory(Protocol):
    def __call__(
        self,
        process_cpu: float = 55.1,
        process_mem: float = 21.2,
        requests_rps: int = 123,
        requests_total: int = 1000,
        requests_successful: int = 10,
        requests_failed: int = 30,
        bytes_in: int = 1000,
        bytes_out: int = 2000,
    ) -> dict[str, Any]: ...


class ResponseEventFactory(Protocol):
    def __call__(
        self,
        method: str = "GET",
        url: str = "/test",
        request_headers: dict[str, str] | None = None,
        request_querystring: bytes | None = None,
        request_body: bytes | None = None,
        request_truncated: bool = False,
        response_headers: dict[str, str] | None = None,
        response_status: int = 200,
        response_body: bytes | None = b'{"test": "json"}',
        response_truncated: bool = False,
        duration: float = 10.3,
    ) -> dict[str, Any]: ...
