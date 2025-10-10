import multiprocessing
from pathlib import Path

from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app


def test_run(mocker: MockerFixture):
    mocked_run = mocker.patch(
        "mrok.cli.commands.proxy.run.proxy.run",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["proxy", "run", "my-identity.json"])
    assert result.exit_code == 0
    mocked_run.assert_called_once_with(
        Path("my-identity.json"), "127.0.0.1", 8000, (multiprocessing.cpu_count() * 2) + 1
    )


def test_run_with_options(mocker: MockerFixture):
    mocked_run = mocker.patch(
        "mrok.cli.commands.proxy.run.proxy.run",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "proxy",
            "run",
            "my-identity.json",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
            "--workers",
            "2",
        ],
    )
    assert result.exit_code == 0
    mocked_run.assert_called_once_with(
        Path("my-identity.json"),
        "0.0.0.0",
        8080,
        2,
    )
