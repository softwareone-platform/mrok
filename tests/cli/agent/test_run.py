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
        shlex.split("agent run asgi my:app ins-1234-5678-0001.json -w 2 --reload -p 4000 -s 5000"),
    )
    assert result.exit_code == 0
    mocked_ziticorn.assert_called_once_with(
        "my:app",
        "ins-1234-5678-0001.json",
        workers=2,
        reload=True,
        publishers_port=4000,
        subscribers_port=5000,
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
            "-w 2 -p 4000 -s 5000 --max-pool-connections 312 "
            "--max-pool-keepalive-connections 11 "
            "--max-pool-keepalive-expiry 3.22 "
            "--max-pool-connect-retries 2"
        ),
    )
    assert result.exit_code == 0
    mocked_sidecar.assert_called_once_with(
        "ins-1234-5678-0001.json",
        expected_target_addr,
        events_enabled=True,
        workers=2,
        max_connections=312,
        max_keepalive_connections=11,
        keepalive_expiry=3.22,
        retries=2,
        publishers_port=4000,
        subscribers_port=5000,
    )
