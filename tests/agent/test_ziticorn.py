from pytest_mock import MockerFixture

from mrok.agent.ziticorn import ZiticornAgent, run


def test_ziticorn_agent(mocker: MockerFixture):
    mocked_app = mocker.MagicMock()
    agent = ZiticornAgent(
        mocked_app,
        "identity.json",
        workers=2,
        reload=True,
        publishers_port=2000,
        subscribers_port=3000,
    )
    assert agent.reload is True
    assert agent.get_asgi_app() == mocked_app


def test_run(mocker: MockerFixture):
    mocked_agent = mocker.MagicMock()
    mocked_agent_ctor = mocker.patch(
        "mrok.agent.ziticorn.ZiticornAgent",
        return_value=mocked_agent,
    )

    run(
        "my.app:app",
        "ziti-identity.json",
        workers=10,
        reload=True,
        publishers_port=4000,
        subscribers_port=5000,
    )

    mocked_agent_ctor.assert_called_once_with(
        "my.app:app",
        "ziti-identity.json",
        workers=10,
        reload=True,
        publishers_port=4000,
        subscribers_port=5000,
    )
    mocked_agent.run.assert_called_once()
