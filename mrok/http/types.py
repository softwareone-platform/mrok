from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from mrok.datastructures import HTTPRequest, HTTPResponse

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

ASGIReceive = Callable[[], Awaitable[Message]]
ASGISend = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, ASGIReceive, ASGISend], Awaitable[None]]
RequestCompleteCallback = Callable[[HTTPRequest], Awaitable | None]
ResponseCompleteCallback = Callable[[HTTPResponse], Awaitable | None]

StreamPair = tuple[asyncio.StreamReader, asyncio.StreamWriter]
