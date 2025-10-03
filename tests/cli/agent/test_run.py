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
        shlex.split("agent run asgi my:app ins-1234-5678-0001.json -w 2 --reload"),
    )
    assert result.exit_code == 0
    mocked_ziticorn.assert_called_once_with(
        "my:app", "ins-1234-5678-0001.json", workers=2, reload=True
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
            f"agent run sidecar ins-1234-5678-0001.json {target_addr}  -w 2 --reload",
        ),
    )
    assert result.exit_code == 0
    mocked_sidecar.assert_called_once_with(
        "ins-1234-5678-0001.json", expected_target_addr, workers=2, reload=True
    )
