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
        server_workers=2,
        events_publishers_port=2000,
        events_subscribers_port=3000,
    )
    assert agent.server_reload is False
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
        server_workers=10,
        upstream_max_connections=15,
        upstream_max_keepalive_connections=3,
        upstream_keepalive_expiry=100,
        upstream_max_connect_retries=6,
        events_publishers_port=4000,
        events_subscribers_port=5000,
    )

    mocked_agent_ctor.assert_called_once_with(
        "ziti-identity.json",
        "target-addr",
        events_enabled=True,
        server_workers=10,
        upstream_max_connections=15,
        upstream_max_keepalive_connections=3,
        upstream_max_connect_retries=6,
        upstream_keepalive_expiry=100,
        events_publishers_port=4000,
        events_subscribers_port=5000,
        events_metrics_collect_interval=5.0,
        server_backlog=2048,
        server_limit_concurrency=None,
        server_limit_max_requests=None,
        server_timeout_keep_alive=5,
        ziti_load_timeout_ms=5000,
    )
    mocked_agent.run.assert_called_once()
