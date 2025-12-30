from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine, Mapping, MutableMapping
from contextlib import AbstractAsyncContextManager
from typing import Any, Never

from mrok.proxy.models import HTTPResponse

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

ASGIReceive = Callable[[], Awaitable[Message]]
ASGISend = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, ASGIReceive, ASGISend], Awaitable[None]]
StatelessLifespan = Callable[[ASGIApp], AbstractAsyncContextManager[None]]
StatefulLifespan = Callable[[ASGIApp], AbstractAsyncContextManager[Mapping[str, Any]]]
Lifespan = StatelessLifespan | StatefulLifespan

LifespanCallback = Callable[[], Awaitable[None]]
ResponseCompleteCallback = Callable[[HTTPResponse], Coroutine[Any, Any, Never]]
