from pytest_mock import MockerFixture

from mrok.agent.ziticorn import ZiticornAgent, run


def test_ziticorn_agent(mocker: MockerFixture):
    mocked_app = mocker.MagicMock()
    agent = ZiticornAgent(
        mocked_app,
        "identity.json",
        server_workers=2,
        server_reload=True,
        events_publishers_port=2000,
        events_subscribers_port=3000,
    )
    assert agent.server_reload is True
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
        server_workers=10,
        server_reload=True,
        events_publishers_port=4000,
        events_subscribers_port=5000,
    )

    mocked_agent_ctor.assert_called_once_with(
        "my.app:app",
        "ziti-identity.json",
        ziti_load_timeout_ms=5000,
        server_workers=10,
        server_reload=True,
        server_backlog=2048,
        server_limit_concurrency=None,
        server_limit_max_requests=None,
        server_timeout_keep_alive=5,
        events_publishers_port=4000,
        events_subscribers_port=5000,
        events_metrics_collect_interval=5.0,
    )
    mocked_agent.run.assert_called_once()
