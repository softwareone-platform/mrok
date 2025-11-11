import multiprocessing

import uvicorn
from fastapi import FastAPI
from textual_serve.server import Server

from mrok.agent.sidecar.store import RequestStore
from mrok.logging import setup_inspector_logging


def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1


def create_inspection_server(store: RequestStore) -> FastAPI:
    inspect_api = FastAPI()

    @inspect_api.get("/requests/")
    async def list_requests(offset: int | None = None) -> list[dict]:
        return store.get_all(starting_from=offset)

    return inspect_api


def run_inspect_api(store: RequestStore, port: int) -> None:
    inspect_api = create_inspection_server(store)
    uvicorn.run(inspect_api, port=port, log_level="warning")


class MServer(Server):
    def initialize_logging(self) -> None:
        setup_inspector_logging(self.console)


def run_textual(port: int) -> None:
    server = MServer("python mrok/agent/sidecar/inspector.py", port=port)
    server.serve()
