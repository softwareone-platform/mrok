from pytest_mock import MockerFixture
from uvicorn.protocols.http.httptools_impl import HttpToolsProtocol as UvHttpToolsProtocol

from mrok.proxy.ziticorn import HttpToolsProtocol


def test_protocol(mocker: MockerFixture):
    mocked_super_init = mocker.patch.object(UvHttpToolsProtocol, "__init__")
    proto = HttpToolsProtocol("10", test=True)
    mocked_super_init.assert_called_once_with("10", test=True)
    assert proto.access_logger.name == "mrok.access"
    assert proto.logger.name == "mrok.proxy"
    assert proto.access_log == proto.access_logger.hasHandlers()
