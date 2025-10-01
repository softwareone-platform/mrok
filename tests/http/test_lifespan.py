from pytest_mock import MockerFixture

from mrok.http.lifespan import MrokLifespan


def test_lifespan(mocker: MockerFixture):
    mocked_config = mocker.MagicMock(loaded=True)

    lifespan = MrokLifespan(mocked_config)
    assert lifespan.config == mocked_config
    assert lifespan.logger.name == "mrok.proxy"
