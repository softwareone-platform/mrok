import asyncio

import pytest
from pytest_mock import MockerFixture

from mrok.proxy.stream import AIONetworkStream, ASGIRequestBodyStream


@pytest.mark.asyncio
async def test_aio_network_stream_read(mocker: MockerFixture):
    m_reader = mocker.AsyncMock()
    m_reader.read.return_value = b"OK"

    aions = AIONetworkStream(m_reader, mocker.MagicMock())
    read_bytes = await aions.read(2)
    assert read_bytes == b"OK"
    m_reader.read.assert_awaited_once_with(2)


@pytest.mark.asyncio
async def test_aio_network_stream_read_timeout(mocker: MockerFixture):
    class FakeReader:
        async def read(self, n: int = -1):
            await asyncio.sleep(0.2)

    aions = AIONetworkStream(FakeReader(), mocker.MagicMock())  # type: ignore[arg-type]
    with pytest.raises(asyncio.TimeoutError):
        await aions.read(5, timeout=0.1)


@pytest.mark.asyncio
async def test_aio_network_stream_write(mocker: MockerFixture):
    m_writer = mocker.AsyncMock()
    m_writer.write = mocker.MagicMock()

    aions = AIONetworkStream(mocker.MagicMock(), m_writer)
    await aions.write(b"OK")
    m_writer.write.assert_called_once_with(b"OK")
    m_writer.drain.assert_awaited_once()


@pytest.mark.asyncio
async def test_aio_network_stream_write_timeout(mocker: MockerFixture):
    class FakeWriter:
        def write(self, data: bytes):
            pass

        async def drain(self):
            await asyncio.sleep(0.2)

    aions = AIONetworkStream(mocker.MagicMock(), FakeWriter())  # type: ignore[arg-type]
    with pytest.raises(asyncio.TimeoutError):
        await aions.write(b"OK", timeout=0.1)


@pytest.mark.asyncio
async def test_aio_network_stream_close(mocker: MockerFixture):
    m_writer = mocker.AsyncMock()
    m_writer.close = mocker.MagicMock()

    aions = AIONetworkStream(mocker.MagicMock(), m_writer)

    await aions.aclose()
    m_writer.close.assert_called_once()
    m_writer.wait_closed.assert_awaited_once()


@pytest.mark.parametrize("readable", [True, False])
def test_aio_network_stream_extra_info_is_readable(
    mocker: MockerFixture,
    readable: bool,
):
    m_sock = mocker.MagicMock()
    m_writer = mocker.MagicMock()
    m_writer.transport = mocker.MagicMock()
    m_writer.transport.get_extra_info.return_value = m_sock

    m_is_readable = mocker.patch("mrok.proxy.stream.is_readable", return_value=readable)

    aions = AIONetworkStream(mocker.MagicMock(), m_writer)

    assert aions.get_extra_info("is_readable") is readable
    m_is_readable.assert_called_once_with(m_sock)
    m_writer.transport.get_extra_info.assert_called_once_with("socket")


def test_aio_network_stream_extra_info_other(
    mocker: MockerFixture,
):
    m_writer = mocker.MagicMock()
    m_writer.transport = mocker.MagicMock()
    m_writer.transport.get_extra_info.return_value = "whatever"

    aions = AIONetworkStream(mocker.MagicMock(), m_writer)

    assert aions.get_extra_info("other_extra") == "whatever"
    m_writer.transport.get_extra_info.assert_called_once_with("other_extra")


@pytest.mark.asyncio
async def test_asgi_request_body_stream():
    messages = [
        {
            "type": "http.request",
            "body": b"first chunk",
            "more_body": True,
        },
        {
            "type": "http.request",
            "body": b"second chunk",
            "more_body": False,
        },
    ]

    msg_iter = iter(messages)

    async def receive():
        await asyncio.sleep(0)
        return next(msg_iter)

    stream = ASGIRequestBodyStream(receive)

    chunks = [chunk async for chunk in stream]
    assert chunks == [b"first chunk", b"second chunk"]


@pytest.mark.asyncio
async def test_asgi_request_body_stream_disconnect():
    messages = [
        {
            "type": "http.disconnect",
        },
    ]

    msg_iter = iter(messages)

    async def receive():
        await asyncio.sleep(0)
        return next(msg_iter)

    stream = ASGIRequestBodyStream(receive)

    with pytest.raises(Exception) as cv:
        await anext(stream)

    assert str(cv.value) == "Client disconnected."


@pytest.mark.asyncio
async def test_asgi_request_body_unknown_msg():
    messages = [
        {
            "type": "whatever",
        },
    ]

    msg_iter = iter(messages)

    async def receive():
        await asyncio.sleep(0)
        return next(msg_iter)

    stream = ASGIRequestBodyStream(receive)

    with pytest.raises(Exception) as cv:
        await anext(stream)

    assert str(cv.value) == "Unexpected asgi message."
