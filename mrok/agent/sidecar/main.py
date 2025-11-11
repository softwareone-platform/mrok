import asyncio
import contextlib
from functools import partial
from pathlib import Path

from mrok.agent.sidecar.app import ForwardApp
from mrok.agent.sidecar.store import RequestStore
from mrok.http.config import MrokBackendConfig
from mrok.http.master import Master
from mrok.http.server import MrokServer


def run_sidecar(
    identity_file: str,
    target_addr: str | Path | tuple[str, int],
    store: RequestStore | None = None,
):
    config = MrokBackendConfig(ForwardApp(target_addr, store=store), identity_file)
    server = MrokServer(config)
    with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
        server.run()


def run(
    identity_file: str,
    target_addr: str | Path | tuple[str, int],
    workers=4,
    reload=False,
    store: RequestStore | None = None,
):
    start_fn = partial(run_sidecar, identity_file, target_addr, store)
    master = Master(start_fn, workers=workers, reload=reload)
    master.run()
