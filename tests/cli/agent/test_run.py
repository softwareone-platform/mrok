import shlex

import pytest
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app


def test_run_asgi(
    mocker: MockerFixture,
):
    mocked_ziticorn = mocker.patch("mrok.cli.commands.agent.run.asgi.ziticorn.run")
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split(
            "agent run asgi my:app ins-1234-5678-0001.json -w 2 --server-reload "
            "--events-publishers-port 4000 "
            "--events-subscribers-port 5000"
        ),
    )
    assert result.exit_code == 0
    mocked_ziticorn.assert_called_once_with(
        "ins-1234-5678-0001.json",
        "my:app",
        ziti_load_timeout_ms=5000,
        server_workers=2,
        server_reload=True,
        server_backlog=2048,
        server_limit_concurrency=None,
        server_limit_max_requests=None,
        server_timeout_keep_alive=5,
        events_publishers_port=4000,
        events_subscribers_port=5000,
        events_metrics_collect_interval=5.0,
    )


@pytest.mark.parametrize(
    ("target_addr", "expected_target_addr"),
    [
        ("/path/to/unix.sock", "/path/to/unix.sock"),
        ("localhost:8000", ("localhost", 8000)),
        (":8000", ("127.0.0.1", 8000)),
    ],
)
def test_run_sidecar(
    mocker: MockerFixture,
    target_addr,
    expected_target_addr,
):
    mocked_sidecar = mocker.patch("mrok.cli.commands.agent.run.sidecar.sidecar.run")
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split(
            f"agent run sidecar ins-1234-5678-0001.json {target_addr} "
            "-w 2 --events-publishers-port 4000 --events-subscribers-port 5000 "
            "--upstream-max-connections 312 "
            "--upstream-max-keepalive-connections 11 "
            "--upstream_keepalive_expiry 3.22 "
            "--upstream-max-connect-retries 2"
        ),
    )
    assert result.exit_code == 0
    mocked_sidecar.assert_called_once_with(
        "ins-1234-5678-0001.json",
        expected_target_addr,
        events_enabled=True,
        server_workers=2,
        upstream_max_connections=312,
        upstream_max_keepalive_connections=11,
        upstream_keepalive_expiry=3.22,
        upstream_max_connect_retries=2,
        events_publishers_port=4000,
        events_subscribers_port=5000,
        events_metrics_collect_interval=5.0,
        server_backlog=2048,
        server_limit_concurrency=None,
        server_limit_max_requests=None,
        server_timeout_keep_alive=5,
        ziti_load_timeout_ms=5000,
    )
