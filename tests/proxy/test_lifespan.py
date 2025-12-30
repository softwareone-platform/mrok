from pytest_mock import MockerFixture

from mrok.proxy.ziticorn import Lifespan


def test_lifespan(mocker: MockerFixture):
    mocked_config = mocker.MagicMock(loaded=True)

    lifespan = Lifespan(mocked_config)
    assert lifespan.config == mocked_config
    assert lifespan.logger.name == "mrok.proxy"
