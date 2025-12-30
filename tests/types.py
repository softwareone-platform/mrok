from collections.abc import Awaitable, Callable, Iterable
from pathlib import PurePath
from typing import Protocol

from textual.app import App
from textual.pilot import Pilot

from mrok.conf import Settings
from mrok.types.proxy import ASGIReceive, ASGISend, Message


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
