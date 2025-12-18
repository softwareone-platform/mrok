import pytest
from pytest_mock import MockerFixture

from mrok.proxy.backend import AIOZitiNetworkBackend
from mrok.proxy.exceptions import InvalidTargetError, TargetUnavailableError


@pytest.mark.asyncio
async def test_connect_tcp(mocker: MockerFixture):
    mocked_ziti_sock = mocker.MagicMock()
    mocked_ziti_ctx = mocker.MagicMock()
    mocked_ziti_ctx.connect.return_value = mocked_ziti_sock
    mocked_ziti_load = mocker.patch(
        "mrok.proxy.backend.openziti.load", return_value=(mocked_ziti_ctx, 0)
    )
    mocked_reader = mocker.MagicMock()
    mocked_writer = mocker.MagicMock()
    mocked_aio_ns = mocker.MagicMock()
    mocked_aio_netstream_ctor = mocker.patch(
        "mrok.proxy.backend.AIONetworkStream", return_value=mocked_aio_ns
    )
    mocked_aio_openconn = mocker.patch(
        "mrok.proxy.backend.asyncio.open_connection", return_value=(mocked_reader, mocked_writer)
    )

    backend = AIOZitiNetworkBackend("my_identity_file.json")
    stream = await backend.connect_tcp("ziti-svc", 0)
    mocked_ziti_load.assert_called_once_with("my_identity_file.json", timeout=10000)
    mocked_ziti_ctx.connect.assert_called_once_with("ziti-svc")
    mocked_aio_netstream_ctor.assert_called_once_with(mocked_reader, mocked_writer)
    mocked_aio_openconn.assert_called_once_with(sock=mocked_ziti_sock)
    assert stream == mocked_aio_ns


@pytest.mark.asyncio
async def test_connect_tcp_context_created_once(mocker: MockerFixture):
    mocked_ziti_sock = mocker.MagicMock()
    mocked_ziti_ctx = mocker.MagicMock()
    mocked_ziti_ctx.connect.return_value = mocked_ziti_sock
    mocked_ziti_load = mocker.patch(
        "mrok.proxy.backend.openziti.load", return_value=(mocked_ziti_ctx, 0)
    )
    mocked_reader = mocker.MagicMock()
    mocked_writer = mocker.MagicMock()
    mocked_aio_ns = mocker.MagicMock()
    mocker.patch("mrok.proxy.backend.AIONetworkStream", return_value=mocked_aio_ns)
    mocker.patch(
        "mrok.proxy.backend.asyncio.open_connection", return_value=(mocked_reader, mocked_writer)
    )

    backend = AIOZitiNetworkBackend("my_identity_file.json")
    _ = await backend.connect_tcp("ziti-svc", 0)
    _ = await backend.connect_tcp("ziti-svc2", 0)
    assert mocked_ziti_load.call_count == 1


@pytest.mark.asyncio
async def test_connect_tcp_load_context_error(mocker: MockerFixture):
    mocker.patch("mrok.proxy.backend.openziti.load", return_value=(mocker.MagicMock(), -20))

    backend = AIOZitiNetworkBackend("my_identity_file.json")
    with pytest.raises(Exception) as cv:
        await backend.connect_tcp("ziti-svc", 0)
    assert str(cv.value) == "Cannot create a Ziti context from the identity file: -20"


@pytest.mark.asyncio
async def test_connect_tcp_target_unavailable(mocker: MockerFixture):
    mocked_ziti_ctx = mocker.MagicMock()
    mocked_ziti_ctx.connect.side_effect = Exception(-24, "service unavailable")
    mocker.patch("mrok.proxy.backend.openziti.load", return_value=(mocked_ziti_ctx, 0))

    backend = AIOZitiNetworkBackend("my_identity_file.json")
    with pytest.raises(TargetUnavailableError):
        await backend.connect_tcp("ziti-svc", 0)


@pytest.mark.asyncio
async def test_connect_tcp_target_doesnt_exist(mocker: MockerFixture):
    mocked_ziti_ctx = mocker.MagicMock()
    mocked_ziti_ctx.connect.side_effect = Exception(-18, "service doesn't exist")
    mocker.patch("mrok.proxy.backend.openziti.load", return_value=(mocked_ziti_ctx, 0))

    backend = AIOZitiNetworkBackend("my_identity_file.json")
    with pytest.raises(InvalidTargetError):
        await backend.connect_tcp("ziti-svc", 0)


@pytest.mark.asyncio
async def test_sleep(mocker: MockerFixture):
    mocked_sleep = mocker.patch("mrok.proxy.backend.asyncio.sleep")
    backend = AIOZitiNetworkBackend("my_identity_file.json")
    await backend.sleep(4)
    mocked_sleep.assert_awaited_once_with(4)
