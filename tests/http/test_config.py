import pytest
from pytest_mock import MockerFixture

from mrok.http.config import MrokBackendConfig
from mrok.http.lifespan import MrokLifespan
from mrok.http.protocol import MrokHttpToolsProtocol


def test_backend_config_init():
    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(fake_asgi_app, "ziti-service", "ziti-identity.json")
    assert config.app == fake_asgi_app
    assert config.loop == "asyncio"
    assert config.http == MrokHttpToolsProtocol
    assert config.lifespan == "auto"
    assert config.backlog == 2048
    assert config.service_name == "ziti-service"
    assert config.identity_file == "ziti-identity.json"


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_backend_config_load():
    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(fake_asgi_app, "ziti-service", "ziti-identity.json")
    config.load()
    assert config.app == fake_asgi_app
    assert config.loop == "asyncio"
    assert config.http_protocol_class == MrokHttpToolsProtocol
    assert config.lifespan_class == MrokLifespan


def test_backend_config_bind_socket(mocker: MockerFixture):
    mocked_ctx = mocker.MagicMock()
    mocked_socket = mocker.MagicMock()
    mocked_ctx.bind.return_value = mocked_socket
    mocked_openziti_load = mocker.patch(
        "mrok.http.config.openziti.load",
        return_value=(mocked_ctx, 0),
    )

    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(fake_asgi_app, "ziti-service", "ziti-identity.json", backlog=4096)
    assert config.bind_socket() == mocked_socket
    mocked_openziti_load.assert_called_once_with("ziti-identity.json")
    mocked_ctx.bind.assert_called_once_with("ziti-service")
    mocked_socket.listen.assert_called_once_with(4096)


def test_backend_config_bind_socket_ziti_error(mocker: MockerFixture):
    mocked_ctx = mocker.MagicMock()
    mocked_socket = mocker.MagicMock()
    mocked_ctx.bind.return_value = mocked_socket
    mocker.patch(
        "mrok.http.config.openziti.load",
        return_value=(None, 1),
    )

    async def fake_asgi_app(scope, receive, send):
        pass

    config = MrokBackendConfig(fake_asgi_app, "ziti-service", "ziti-identity.json", backlog=4096)
    with pytest.raises(RuntimeError) as cv:
        config.bind_socket()

    assert str(cv.value) == "Failed to load Ziti identity from ziti-identity.json: 1"


def test_backend_config_configure_logging(mocker: MockerFixture):
    mocked_settings = mocker.MagicMock()
    mocker.patch("mrok.http.config.get_settings", return_value=mocked_settings)
    mocked_setup_logging = mocker.patch("mrok.http.config.setup_logging")

    async def fake_asgi_app(scope, receive, send):
        pass

    MrokBackendConfig(fake_asgi_app, "ziti-service", "ziti-identity.json", backlog=4096)
    mocked_setup_logging.assert_called_once_with(mocked_settings)
