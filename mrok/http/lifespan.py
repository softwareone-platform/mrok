import logging
from collections.abc import Awaitable, Callable

from uvicorn.config import Config
from uvicorn.lifespan.on import LifespanOn

AsyncCallback = Callable[[], Awaitable[None]]


class MrokLifespan(LifespanOn):
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.logger = logging.getLogger("mrok.proxy")


class LifespanWrapper:
    def __init__(
        self, app, on_startup: AsyncCallback | None = None, on_shutdown: AsyncCallback | None = None
    ):
        self.app = app
        self.on_startup = on_startup
        self.on_shutdown = on_shutdown

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                event = await receive()
                if event["type"] == "lifespan.startup":
                    if self.on_startup:
                        await self.on_startup()
                    await send({"type": "lifespan.startup.complete"})

                elif event["type"] == "lifespan.shutdown":
                    if self.on_shutdown:
                        await self.on_shutdown()
                    await send({"type": "lifespan.shutdown.complete"})
                    break
        else:
            await self.app(scope, receive, send)
