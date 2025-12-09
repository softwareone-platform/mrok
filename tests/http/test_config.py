import pytest
from pytest_mock import MockerFixture

from mrok.http.config import MrokBackendConfig
from mrok.http.lifespan import MrokLifespan
from mrok.http.protocol import MrokHttpToolsProtocol


def test_backend_config_init(ziti_identity_file: str):
    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(fake_asgi_app, ziti_identity_file)
    assert config.app == fake_asgi_app
    assert config.loop == "asyncio"
    assert config.http == MrokHttpToolsProtocol
    assert config.lifespan == "auto"
    assert config.backlog == 2048
    assert config.service_name == "ext-1234-5678"
    assert config.identity_name == "ins-1234-5678-0001.ext-1234-5678"
    assert config.identity_file == ziti_identity_file


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_backend_config_load(ziti_identity_file: str):
    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(fake_asgi_app, ziti_identity_file)
    config.load()
    assert config.app == fake_asgi_app
    assert config.loop == "asyncio"
    assert config.http_protocol_class == MrokHttpToolsProtocol
    assert config.lifespan_class == MrokLifespan


def test_backend_config_bind_socket(mocker: MockerFixture, ziti_identity_file: str):
    mocked_ctx = mocker.MagicMock()
    mocked_socket = mocker.MagicMock()
    mocked_ctx.bind.return_value = mocked_socket
    mocked_openziti_load = mocker.patch(
        "mrok.http.config.openziti.load",
        return_value=(mocked_ctx, 0),
    )

    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(
        fake_asgi_app, ziti_identity_file, backlog=4096, ziti_load_timeout_ms=1234
    )
    assert config.bind_socket() == mocked_socket
    mocked_openziti_load.assert_called_once_with(ziti_identity_file, timeout=1234)
    mocked_ctx.bind.assert_called_once_with(
        "ext-1234-5678",
    )
    mocked_socket.listen.assert_called_once_with(4096)


def test_backend_config_bind_socket_ziti_error(mocker: MockerFixture, ziti_identity_file: str):
    mocked_ctx = mocker.MagicMock()
    mocked_socket = mocker.MagicMock()
    mocked_ctx.bind.return_value = mocked_socket
    mocker.patch(
        "mrok.http.config.openziti.load",
        return_value=(None, 1),
    )

    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(fake_asgi_app, ziti_identity_file, backlog=4096)
    with pytest.raises(RuntimeError) as cv:
        config.bind_socket()

    assert str(cv.value) == f"Failed to load Ziti identity from {ziti_identity_file}: 1"
