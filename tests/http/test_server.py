import pytest
from pytest_mock import MockerFixture

from mrok.http.config import MrokBackendConfig
from mrok.http.server import MrokServer


@pytest.mark.asyncio
async def test_serve(mocker: MockerFixture):
    mocked_socket = mocker.MagicMock()
    mocker.patch.object(MrokBackendConfig, "bind_socket", return_value=mocked_socket)
    mocked_inner_serve = mocker.patch.object(MrokServer, "_serve")

    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(fake_asgi_app, "ziti-service", "ziti-identity.json")

    server = MrokServer(config)
    await server.serve()
    mocked_inner_serve.assert_awaited_once_with([mocked_socket])


@pytest.mark.asyncio
async def test_serve_with_socket(mocker: MockerFixture):
    mocked_socket = mocker.MagicMock()
    mocked_bind = mocker.patch.object(MrokBackendConfig, "bind_socket")
    mocked_inner_serve = mocker.patch.object(MrokServer, "_serve")

    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(fake_asgi_app, "ziti-service", "ziti-identity.json")

    server = MrokServer(config)
    await server.serve([mocked_socket])
    mocked_inner_serve.assert_awaited_once_with([mocked_socket])
    mocked_bind.assert_not_called()
