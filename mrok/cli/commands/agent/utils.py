import asyncio
import multiprocessing
import signal

import uvicorn
from aiohttp import web
from fastapi import FastAPI
from textual_serve.server import Server

from mrok.agent.sidecar.store import RequestStore
from mrok.conf import get_settings
from mrok.logging import setup_inspector_logging


def number_of_workers() -> int:
    return (multiprocessing.cpu_count() * 2) + 1


def inspector_port() -> int:
    settings = get_settings()
    return settings.sidecar.textual_port


def store_api_port() -> int:
    settings = get_settings()
    return settings.sidecar.store_port


def get_textual_command() -> str:
    settings = get_settings()
    return settings.sidecar.textual_command


def create_inspection_server(store: RequestStore) -> FastAPI:
    inspect_api = FastAPI()

    @inspect_api.get("/requests/")
    async def list_requests(offset: int = 0) -> list[dict]:
        return store.get_all(offset=offset)

    return inspect_api


def run_inspect_api(store: RequestStore, port: int, log_level: str = "warning") -> None:
    inspect_api = create_inspection_server(store)
    uvicorn.run(inspect_api, port=port, log_level=log_level)


class MServer(Server):
    def __init__(self, command: str, port: int, api_port: int, store: RequestStore):
        super().__init__(command, port=port, title="MROK Web inspector")
        self.api_port = api_port
        self.store = store
        self.store_api_runner = None

    def initialize_logging(self) -> None:
        setup_inspector_logging(self.console)

    def serve(self, debug: bool = False) -> None:  # pragma: no cover
        self.debug = debug
        self.initialize_logging()

        try:
            loop = asyncio.get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()

        loop.add_signal_handler(signal.SIGINT, self.request_exit)
        loop.add_signal_handler(signal.SIGTERM, self.request_exit)

        loop.run_until_complete(self._serve(loop))

    async def _serve(self, loop: asyncio.AbstractEventLoop):  # pragma: no cover
        textual_app = await self._make_app()
        api_app = create_inspection_server(self.store)

        textual_runner = web.AppRunner(textual_app)
        await textual_runner.setup()
        textual_site = web.TCPSite(textual_runner, self.host, self.port)
        await textual_site.start()

        stop_event = asyncio.Event()

        def stop() -> None:
            stop_event.set()

        loop.add_signal_handler(signal.SIGINT, stop)
        loop.add_signal_handler(signal.SIGTERM, stop)

        config = uvicorn.Config(
            api_app,
            host=self.host,
            port=self.api_port,
            loop="asyncio",
            log_level="info",
        )
        api_server = uvicorn.Server(config)

        async def start_fastapi():
            await api_server.serve()

        fastapi_task = asyncio.create_task(start_fastapi())

        try:
            await stop_event.wait()
        finally:
            api_server.should_exit = True
            await fastapi_task
            await textual_runner.cleanup()


def run_textual(port: int, api_port: int, store: RequestStore) -> None:
    server = MServer(get_textual_command(), port=port, api_port=api_port, store=store)
    server.serve()
