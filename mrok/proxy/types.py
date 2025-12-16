from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine, MutableMapping
from typing import Any, Never

from mrok.proxy.datastructures import HTTPResponse

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

ASGIReceive = Callable[[], Awaitable[Message]]
ASGISend = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, ASGIReceive, ASGISend], Awaitable[None]]
LifespanCallback = Callable[[], Awaitable[None]]
ResponseCompleteCallback = Callable[[HTTPResponse], Coroutine[Any, Any, Never]]
