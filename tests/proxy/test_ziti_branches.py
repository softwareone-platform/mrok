# import asyncio
# import time

# import pytest

# from mrok.proxy.ziti import (
#     CachedStreamWriter,
#     ReaderProxy,
#     ZitiConnectionManager,
# )


# class DummyCtx:
#     def connect(self, ext, term):
#         return object()


# class ReaderRaise:
#     async def read(self, n=-1):
#         raise RuntimeError("read-fail")

#     async def readexactly(self, n):
#         raise RuntimeError("readexactly-fail")

#     async def readline(self):
#         raise RuntimeError("readline-fail")

#     def at_eof(self):
#         return False


# class WriterDrainRaise:
#     def write(self, data: bytes):
#         pass

#     async def drain(self):
#         raise RuntimeError("drain-fail")

#     def close(self):
#         pass

#     async def wait_closed(self):
#         pass


# class WriterBadClose:
#     def write(self, data: bytes):
#         pass

#     async def drain(self):
#         await asyncio.sleep(0)

#     def close(self):
#         raise RuntimeError("close-fail")

#     async def wait_closed(self):
#         raise RuntimeError("wait-fail")


# class BadUnderlying:
#     def __getattr__(self, name):
#         raise RuntimeError("bad")


# def make_manager():
#     manager = object.__new__(ZitiConnectionManager)
#     manager._ziti_ctx = DummyCtx()
#     manager._ttl = 60.0
#     manager._purge_interval = 10.0
#     manager._cache = {}
#     manager._lock = asyncio.Lock()
#     manager._in_progress = {}
#     manager._purge_task = None
#     return manager


# @pytest.mark.asyncio
# async def test_readerproxy_invalidates_on_read():
#     mgr = make_manager()
#     key = ("ext", "inst")
#     r = ReaderProxy(ReaderRaise(), key, mgr)
#     w = CachedStreamWriter(type("W", (), {})(), key, mgr)
#     async with mgr._lock:
#         mgr._cache[key] = (r, w, time.time())

#     with pytest.raises(RuntimeError):
#         await r.read()

#     # allow scheduled invalidate task to run
#     await asyncio.sleep(0)
#     async with mgr._lock:
#         assert key not in mgr._cache


# @pytest.mark.asyncio
# async def test_writerproxy_invalidates_on_drain():
#     mgr = make_manager()
#     key = ("ext", "inst")
#     reader = type("R", (), {"at_eof": lambda self: False})()
#     w_inner = WriterDrainRaise()
#     w = CachedStreamWriter(w_inner, key, mgr)
#     r = ReaderProxy(reader, key, mgr)
#     async with mgr._lock:
#         mgr._cache[key] = (r, w, time.time())

#     with pytest.raises(RuntimeError):
#         await w.drain()

#     await asyncio.sleep(0)
#     async with mgr._lock:
#         assert key not in mgr._cache


# @pytest.mark.asyncio
# async def test_close_writer_pair_handles_exceptions():
#     mgr = make_manager()
#     pair = (
#         ReaderProxy(type("R", (), {"at_eof": lambda self: True})(), ("e", "t"), mgr),
#         CachedStreamWriter(WriterBadClose(), ("e", "t"), mgr),
#     )
#     # should not raise
#     await mgr._close_writer_pair(pair)


# @pytest.mark.asyncio
# async def test_open_connection_non_awaitable(monkeypatch):
#     mgr = make_manager()

#     async def fake_open_conn(sock=None):
#         return type("R", (), {"at_eof": lambda self: False})(), WriterBadClose()

#     # first test awaitable path
#     monkeypatch.setattr(asyncio, "open_connection", fake_open_conn)
#     r, w = await mgr.get("svc.instance")
#     assert hasattr(r, "at_eof")
#     assert hasattr(w, "close")

#     # now monkeypatch to a non-awaitable function
#     def fake_open_conn_nonawait(sock=None):
#         return type("R", (), {"at_eof": lambda self: False})(), WriterBadClose()

#     monkeypatch.setattr(asyncio, "open_connection", fake_open_conn_nonawait)
#     r2, w2 = await mgr.get("svc.other")
#     assert hasattr(r2, "at_eof")
#     assert hasattr(w2, "close")


# def test_is_writer_closed_exception_branch():
#     mgr = make_manager()
#     fake_writer = type("FW", (), {})()
#     # underlying that raises when accessed
#     fake_writer._underlying = BadUnderlying()
#     wp = CachedStreamWriter(fake_writer, ("e", "t"), mgr)
#     assert mgr._is_writer_closed(wp)
