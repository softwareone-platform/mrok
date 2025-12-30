from pytest_mock import MockerFixture

from mrok.agent.sidecar import main


def test_sidecar_agent(mocker: MockerFixture):
    mocked_app = mocker.MagicMock()
    mocked_app_ctor = mocker.patch(
        "mrok.agent.sidecar.main.SidecarProxyApp",
        return_value=mocked_app,
    )
    agent = main.SidecarAgent(
        "identity.json",
        ":8000",
        workers=2,
        publishers_port=2000,
        subscribers_port=3000,
    )
    assert agent.reload is False
    assert agent.get_asgi_app() == mocked_app
    mocked_app_ctor.assert_called_once_with(
        ":8000",
        max_connections=10,
        max_keepalive_connections=None,
        keepalive_expiry=None,
        retries=0,
    )


def test_run(mocker: MockerFixture):
    mocked_agent = mocker.MagicMock()
    mocked_agent_ctor = mocker.patch(
        "mrok.agent.sidecar.main.SidecarAgent",
        return_value=mocked_agent,
    )

    main.run(
        "ziti-identity.json",
        "target-addr",
        workers=10,
        max_connections=15,
        max_keepalive_connections=3,
        keepalive_expiry=100,
        retries=6,
        publishers_port=4000,
        subscribers_port=5000,
    )

    mocked_agent_ctor.assert_called_once_with(
        "ziti-identity.json",
        "target-addr",
        events_enabled=True,
        workers=10,
        max_connections=15,
        max_keepalive_connections=3,
        retries=6,
        keepalive_expiry=100,
        publishers_port=4000,
        subscribers_port=5000,
    )
    mocked_agent.run.assert_called_once()
