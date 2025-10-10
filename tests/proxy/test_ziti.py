# import asyncio
# import time
# from typing import Any

# import openziti
# import pytest

# from mrok.proxy.ziti import CachedStreamWriter, ReaderProxy, ZitiConnectionManager


# class DummyCtx:
#     def __init__(self):
#         self.connect_calls = []

#     def connect(self, ext, term):
#         # return a dummy token (not a real socket) since we monkeypatch
#         # asyncio.open_connection in tests
#         self.connect_calls.append((ext, term))
#         return object()


# class FakeReader:
#     def __init__(self):
#         self.closed = False

#     async def read(self, n: int = -1) -> bytes:
#         return b"data"

#     async def readexactly(self, n: int) -> bytes:
#         return b"data"

#     async def readline(self) -> bytes:
#         return b"\r\n"

#     def at_eof(self) -> bool:
#         return False


# class FakeTransport:
#     def __init__(self, closing=False):
#         self._closing = closing

#     def is_closing(self) -> bool:
#         return self._closing


# class FakeUnderlyingWriter:
#     def __init__(self, transport=None):
#         self.transport = transport
#         self._closed = False

#     def write(self, data: bytes) -> None:
#         pass

#     async def drain(self) -> None:
#         await asyncio.sleep(0)

#     def close(self) -> None:
#         self._closed = True

#     async def wait_closed(self) -> None:
#         await asyncio.sleep(0)


# class FakeWriter:
#     def __init__(self, transport=None):
#         # emulate attribute access used by _WriterProxy and real writers:
#         # the underlying writer exposes a `transport` attribute. Keep
#         # _underlying pointing to self for compatibility with proxy code.
#         self.transport = transport
#         self._underlying = self

#     def write(self, data: bytes) -> None:
#         pass

#     async def drain(self) -> None:
#         await asyncio.sleep(0)

#     def close(self) -> None:
#         # reflect behaviour accessible from proxies
#         try:
#             self.transport = None
#         except Exception:
#             pass

#     async def wait_closed(self) -> None:
#         await asyncio.sleep(0)


# @pytest.mark.asyncio
# async def test_get_creates_and_caches(monkeypatch):
#     ctx = DummyCtx()

#     def fake_open_connection(sock=None):
#         return FakeReader(), FakeWriter(transport=FakeTransport(False))

#     monkeypatch.setattr(asyncio, "open_connection", fake_open_connection)

#     manager = object.__new__(ZitiConnectionManager)
#     # minimal manual init
#     manager._ziti_ctx = ctx
#     manager._ttl = 60.0
#     manager._purge_interval = 10.0
#     manager._cache = {}
#     manager._lock = asyncio.Lock()
#     manager._in_progress = {}
#     manager._purge_task = None

#     r1, w1 = await manager.get("svc.instance")
#     assert hasattr(r1, "read")
#     assert hasattr(w1, "write")

#     # second call returns the same cached proxies
#     r2, w2 = await manager.get("svc.instance")
#     assert r1 is r2
#     assert w1 is w2


# @pytest.mark.asyncio
# async def test_invalidate_and_recreate(monkeypatch):
#     ctx = DummyCtx()

#     call_count = {"open_conn": 0}

#     def fake_open_connection(sock=None):
#         call_count["open_conn"] += 1
#         return FakeReader(), FakeWriter(transport=FakeTransport(False))

#     monkeypatch.setattr(asyncio, "open_connection", fake_open_connection)

#     manager = object.__new__(ZitiConnectionManager)
#     manager._ziti_ctx = ctx
#     manager._ttl = 60.0
#     manager._purge_interval = 10.0
#     manager._cache = {}
#     manager._lock = asyncio.Lock()
#     manager._in_progress = {}
#     manager._purge_task = None

#     await manager.get("svc.instance")
#     assert call_count["open_conn"] == 1

#     # invalidate should remove cached and on next get a new connection is created
#     await manager.invalidate(("svc", "instance"))
#     await manager.get("svc.instance")
#     assert call_count["open_conn"] == 2


# @pytest.mark.asyncio
# async def test_purge_once_eviction(monkeypatch):
#     ctx = DummyCtx()

#     def fake_open_connection(sock=None):
#         return FakeReader(), FakeWriter(transport=FakeTransport(False))

#     monkeypatch.setattr(asyncio, "open_connection", fake_open_connection)

#     manager = object.__new__(ZitiConnectionManager)
#     manager._ziti_ctx = ctx
#     manager._ttl = 1.0
#     manager._purge_interval = 10.0
#     manager._cache = {}
#     manager._lock = asyncio.Lock()
#     manager._in_progress = {}
#     manager._purge_task = None

#     r, w = await manager.get("svc.instance")
#     # mark the cached entry as old
#     key = ("svc", "instance")
#     async with manager._lock:
#         manager._cache[key] = (r, w, time.time() - (manager._ttl + 10))

#     await manager._purge_once()
#     async with manager._lock:
#         assert key not in manager._cache


# def test_is_writer_closed_true_and_false():
#     manager = object.__new__(ZitiConnectionManager)
#     # no need to fully init for this helper
#     fake_writer1 = FakeWriter(transport=None)
#     wp1 = CachedStreamWriter(fake_writer1, ("e", "t"), manager)
#     assert manager._is_writer_closed(wp1)

#     fake_writer2 = FakeWriter(transport=FakeTransport(False))
#     wp2 = CachedStreamWriter(fake_writer2, ("e", "t"), manager)
#     assert not manager._is_writer_closed(wp2)


# @pytest.mark.asyncio
# async def test_stop_cancels_and_closes(monkeypatch):
#     ctx = DummyCtx()

#     def fake_open_connection(sock=None):
#         return FakeReader(), FakeWriter(transport=FakeTransport(False))

#     monkeypatch.setattr(asyncio, "open_connection", fake_open_connection)

#     manager = object.__new__(ZitiConnectionManager)
#     manager._ziti_ctx = ctx
#     manager._ttl = 60.0
#     manager._purge_interval = 10.0
#     manager._cache = {}
#     manager._lock = asyncio.Lock()
#     manager._in_progress = {}
#     # create a real task to ensure cancel path exercised
#     manager._purge_task = asyncio.create_task(asyncio.sleep(3600))

#     await manager.get("svc.instance")
#     await manager.stop()
#     # after stop cache must be cleared
#     async with manager._lock:
#         assert not manager._cache


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
# async def test_readerproxy_invalidates_on_readexactly_and_readline():
#     mgr = make_manager()
#     key = ("ext2", "inst2")
#     r = ReaderProxy(ReaderRaise(), key, mgr)
#     w = CachedStreamWriter(type("W", (), {})(), key, mgr)
#     async with mgr._lock:
#         mgr._cache[key] = (r, w, time.time())

#     with pytest.raises(RuntimeError):
#         await r.readexactly(4)

#     with pytest.raises(RuntimeError):
#         await r.readline()

#     # allow scheduled invalidate tasks
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
# async def test_writerproxy_invalidates_on_write():
#     mgr = make_manager()
#     key = ("extw", "instw")

#     class WriterWriteRaise:
#         def write(self, data: bytes):
#             raise RuntimeError("write-fail")

#         async def drain(self):
#             await asyncio.sleep(0)

#         def close(self):
#             pass

#         async def wait_closed(self):
#             pass

#     w_inner = WriterWriteRaise()
#     w = CachedStreamWriter(w_inner, key, mgr)
#     r = ReaderProxy(type("R", (), {"at_eof": lambda self: False})(), key, mgr)
#     async with mgr._lock:
#         mgr._cache[key] = (r, w, time.time())

#     with pytest.raises(RuntimeError):
#         w.write(b"x")

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
# async def test_purge_once_handles_exceptions_on_close_and_wait():
#     mgr = make_manager()
#     key = ("svc", "old")
#     # Put a WriterBadClose (raises on close and wait_closed) into cache
#     r = ReaderProxy(type("R", (), {"at_eof": lambda self: False})(), key, mgr)
#     w = CachedStreamWriter(WriterBadClose(), key, mgr)
#     async with mgr._lock:
#         mgr._cache[key] = (r, w, time.time() - (mgr._ttl + 10))

#     # should not raise
#     await mgr._purge_once()


# def test_constructor_raises_on_bad_identity(monkeypatch):
#     # make openziti.load return an error code
#     monkeypatch.setattr(openziti, "load", lambda identity: (None, 1))
#     with pytest.raises(Exception) as excinfo:
#         ZitiConnectionManager("/nonexistent/identity")
#     assert "Cannot create a Ziti context" in str(excinfo.value)


# @pytest.mark.asyncio
# async def test_stale_cached_entry_is_recreated(monkeypatch):
#     def fake_open_connection(sock=None):
#         return FakeReader(), FakeWriter(transport=FakeTransport(False))

#     monkeypatch.setattr(asyncio, "open_connection", fake_open_connection)

#     mgr = make_manager()
#     key = ("svc", "instance")

#     # create a stale cached pair: writer has no transport -> considered closed
#     stale_r = ReaderProxy(type("R", (), {"at_eof": lambda self: False})(), key, mgr)
#     stale_w = CachedStreamWriter(FakeWriter(transport=None), key, mgr)
#     async with mgr._lock:
#         mgr._cache[key] = (stale_r, stale_w, time.time())

#     r_new, w_new = await mgr.get("svc.instance")
#     assert r_new is not stale_r
#     assert w_new is not stale_w


# def test_constructor_success(monkeypatch):
#     # simulate successful openziti.load
#     fake_ctx = DummyCtx()
#     monkeypatch.setattr(openziti, "load", lambda identity: (fake_ctx, 0))
#     mgr = ZitiConnectionManager("/some/identity", ttl_seconds=5.0, purge_interval=1.0)
#     assert mgr._ziti_ctx is fake_ctx
#     assert mgr._ttl == 5.0


# @pytest.mark.asyncio
# async def test_ensure_purge_loop_cancel():
#     mgr = make_manager()
#     # set a short purge interval to create the purge task
#     mgr._purge_interval = 0.01
#     await mgr._ensure_purge_task()
#     task = mgr._purge_task
#     assert task is not None
#     # cancel the task and allow the loop to process cancellation
#     task.cancel()
#     await asyncio.sleep(0)


# @pytest.mark.asyncio
# async def test_evict_expired_locked_direct():
#     mgr = make_manager()
#     key = ("extx", "instx")
#     r = ReaderProxy(type("R", (), {"at_eof": lambda self: False})(), key, mgr)
#     w = CachedStreamWriter(FakeWriter(transport=None), key, mgr)
#     async with mgr._lock:
#         mgr._cache[key] = (r, w, time.time() - (mgr._ttl + 5))
#         now = time.time()
#         to_close = mgr._evict_expired_locked(now)
#         assert len(to_close) == 1
#         assert key not in mgr._cache


# @pytest.mark.asyncio
# async def test_concurrent_get_serialization(monkeypatch):
#     # ensure that concurrent get calls for same key serialise and only one
#     # underlying connection is created
#     ctx = DummyCtx()

#     async def slow_open_connection(sock=None):
#         await asyncio.sleep(0.05)
#         return FakeReader(), FakeWriter(transport=FakeTransport(False))

#     monkeypatch.setattr(asyncio, "open_connection", slow_open_connection)

#     mgr = make_manager()
#     mgr._ziti_ctx = ctx

#     # start two concurrent gets
#     t1 = asyncio.create_task(mgr.get("svc.instance"))
#     await asyncio.sleep(0)  # let t1 start and create the per-key lock
#     t2 = asyncio.create_task(mgr.get("svc.instance"))

#     r1, w1 = await t1
#     r2, w2 = await t2
#     # both are proxies
#     assert hasattr(r1, "read")
#     assert hasattr(w1, "write")
#     assert r1 is r2
#     assert w1 is w2
#     # connect should have been called once (DummyCtx.connect appends calls)
#     assert len(ctx.connect_calls) == 1


# @pytest.mark.asyncio
# async def test_stop_handles_wait_closed_exceptions():
#     mgr = make_manager()
#     key = ("svc", "badclose")
#     r = ReaderProxy(type("R", (), {"at_eof": lambda self: False})(), key, mgr)
#     w = CachedStreamWriter(WriterBadClose(), key, mgr)
#     async with mgr._lock:
#         mgr._cache[key] = (r, w, time.time())

#     # should not raise
#     await mgr.stop()


# @pytest.mark.asyncio
# async def test_open_connection_non_awaitable(monkeypatch):
#     mgr = make_manager()

#     def fake_open_conn(sock: Any = None):
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
