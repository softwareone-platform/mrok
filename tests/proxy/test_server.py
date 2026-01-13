import pytest
from pytest_mock import MockerFixture

from mrok.proxy.ziticorn import BackendConfig, Server


@pytest.mark.asyncio
async def test_serve(mocker: MockerFixture, ziti_identity_file: str):
    mocked_socket = mocker.MagicMock()
    mocker.patch.object(BackendConfig, "bind_socket", return_value=mocked_socket)
    mocked_inner_serve = mocker.patch.object(Server, "_serve")

    async def fake_asgi_app(scope, receive, send):
        pass

    config = BackendConfig(fake_asgi_app, ziti_identity_file)

    server = Server(config)
    await server.serve()
    mocked_inner_serve.assert_awaited_once_with([mocked_socket])


@pytest.mark.asyncio
async def test_serve_with_socket(mocker: MockerFixture, ziti_identity_file: str):
    mocked_socket = mocker.MagicMock()
    mocked_bind = mocker.patch.object(BackendConfig, "bind_socket")
    mocked_inner_serve = mocker.patch.object(Server, "_serve")

    async def fake_asgi_app(scope, receive, send):
        pass

    config = BackendConfig(fake_asgi_app, ziti_identity_file)

    server = Server(config)
    await server.serve([mocked_socket])
    mocked_inner_serve.assert_awaited_once_with([mocked_socket])
    mocked_bind.assert_not_called()
