from pytest_mock import MockerFixture

from mrok.http.protocol import HttpToolsProtocol, MrokHttpToolsProtocol


def test_protocol(mocker: MockerFixture):
    mocked_super_init = mocker.patch.object(HttpToolsProtocol, "__init__")
    proto = MrokHttpToolsProtocol("10", test=True)
    mocked_super_init.assert_called_once_with("10", test=True)
    assert proto.access_logger.name == "mrok.access"
    assert proto.logger.name == "mrok.proxy"
    assert proto.access_log == proto.access_logger.hasHandlers()
