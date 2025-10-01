import asyncio
import contextlib
import os
from functools import partial

from mrok.http.config import ASGIApplication, MrokBackendConfig
from mrok.http.master import Master
from mrok.http.server import MrokServer


def run_ziticorn(app: ASGIApplication | str, identity_file: str):
    import sys

    sys.path.insert(0, os.getcwd())
    config = MrokBackendConfig(app, identity_file)
    server = MrokServer(config)
    with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
        server.run()


def run(
    app: ASGIApplication | str,
    identity_file: str,
    workers: int = 4,
    reload: bool = False,
):
    start_fn = partial(run_ziticorn, app, identity_file)
    master = Master(start_fn, workers=workers, reload=reload)
    master.run()
