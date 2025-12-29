import multiprocessing
from pathlib import Path

from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app


def test_run(mocker: MockerFixture):
    mocked_run = mocker.patch(
        "mrok.cli.commands.frontend.run.frontend.run",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["frontend", "run", "my-identity.json"])
    assert result.exit_code == 0
    mocked_run.assert_called_once_with(
        Path("my-identity.json"),
        "127.0.0.1",
        8000,
        (multiprocessing.cpu_count() * 2) + 1,
        max_connections=1000,
        max_keepalive_connections=100,
        keepalive_expiry=300.0,
    )


def test_run_with_options(mocker: MockerFixture):
    mocked_run = mocker.patch(
        "mrok.cli.commands.frontend.run.frontend.run",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "frontend",
            "run",
            "my-identity.json",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
            "--workers",
            "2",
            "--max-pool-connections",
            "312",
            "--max-pool-keepalive-connections",
            "11",
            "--max-pool-keepalive-expiry",
            "3.22",
        ],
    )
    assert result.exit_code == 0
    mocked_run.assert_called_once_with(
        Path("my-identity.json"),
        "0.0.0.0",
        8080,
        2,
        max_connections=312,
        max_keepalive_connections=11,
        keepalive_expiry=3.22,
    )
