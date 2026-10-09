from pytest_mock import MockerFixture
from uvicorn.protocols.http.httptools_impl import HttpToolsProtocol as UvHttpToolsProtocol

from mrok.proxy.ziticorn import HttpToolsProtocol


def test_protocol(mocker: MockerFixture):
    mocked_super_init = mocker.patch.object(UvHttpToolsProtocol, "__init__")
    cfg = mocker.MagicMock()
    cfg.identity.mrok.extension = "EXT-1234-5678"
    proto = HttpToolsProtocol(cfg, test=True)
    mocked_super_init.assert_called_once_with(cfg, test=True)
    assert proto.access_logger.name == "mrok.access"
    assert proto.access_logger.extra == {"extension": "EXT-1234-5678"}
    assert proto.logger.name == "mrok.proxy"
    assert proto.access_log == proto.access_logger.hasHandlers()


def test_access_logger_adapter_prefixes_extension(mocker: MockerFixture):
    cfg = mocker.MagicMock()
    cfg.identity.mrok.extension = "EXT-1234-5678"
    mocker.patch.object(UvHttpToolsProtocol, "__init__")
    proto = HttpToolsProtocol(cfg)
    msg, kwargs = proto.access_logger.process('%s - "%s %s HTTP/%s" %d', {})
    assert msg == '[EXT-1234-5678] %s - "%s %s HTTP/%s" %d'
    assert kwargs["extra"] == {"extension": "EXT-1234-5678"}
