from collections.abc import Iterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, ParamSpec, Protocol

from mrok.types.proxy import ASGIApp, ASGIReceive, ASGISend, Lifespan, Scope

P = ParamSpec("P")


class ASGIMiddleware(Protocol[P]):
    def __call__(
        self, app: ASGIApp, /, *args: P.args, **kwargs: P.kwargs
    ) -> ASGIApp: ...  # pragma: no cover


class Middleware:
    def __init__(self, cls: ASGIMiddleware[P], *args: P.args, **kwargs: P.kwargs) -> None:
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    def __iter__(self) -> Iterator[Any]:
        as_tuple = (self.cls, self.args, self.kwargs)
        return iter(as_tuple)


class ASGIAppWrapper:
    def __init__(
        self,
        app: ASGIApp,
        lifespan: Lifespan | None = None,
    ) -> None:
        self.app = app
        self.lifespan = lifespan
        self.middlware: list[Middleware] = []
        self.middleare_stack: ASGIApp | None = None

    def add_middleware(self, cls: ASGIMiddleware[P], *args: P.args, **kwargs: P.kwargs):
        self.middlware.insert(0, Middleware(cls, *args, **kwargs))

    def build_middleware_stack(self):
        app = self.app
        for cls, args, kwargs in reversed(self.middlware):
            app = cls(app, *args, **kwargs)
        return app

    def get_starlette_lifespan(self):
        router = getattr(self.app, "router", None)
        if router is None:
            return None
        return getattr(router, "lifespan_context", None)

    @asynccontextmanager
    async def merge_lifespan(self, app: ASGIApp):
        async with AsyncExitStack() as stack:
            state: dict[Any, Any] = {}
            if self.lifespan is not None:
                outer_state = await stack.enter_async_context(self.lifespan(app))
                state.update(outer_state or {})
            starlette_lifespan = self.get_starlette_lifespan()
            if starlette_lifespan is not None:
                inner_state = await stack.enter_async_context(starlette_lifespan(app))
                state.update(inner_state or {})
            yield state

    async def handle_lifespan(self, scope: Scope, receive: ASGIReceive, send: ASGISend) -> None:
        started = False
        app: Any = scope.get("app")
        await receive()
        try:
            async with self.merge_lifespan(app) as state:
                if state:
                    if "state" not in scope:
                        raise RuntimeError('"state" is unsupported by the current ASGI Server.')
                    scope["state"].update(state)
                await send({"type": "lifespan.startup.complete"})
                started = True
                await receive()
        except Exception as e:  # pragma: no cover
            if started:
                await send({"type": "lifespan.shutdown.failed", "message": str(e)})
            else:
                await send({"type": "lifespan.startup.failed", "message": str(e)})
            raise
        else:
            await send({"type": "lifespan.shutdown.complete"})

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend) -> None:
        if self.middleare_stack is None:  # pragma: no branch
            self.middleware_stack = self.build_middleware_stack()
        if scope["type"] == "lifespan":
            scope["app"] = self
            await self.handle_lifespan(scope, receive, send)
            return

        await self.middleware_stack(scope, receive, send)
