import shlex

from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app


def test_dev_console(
    mocker: MockerFixture,
):
    mocked_app = mocker.MagicMock()
    mocked_app_ctor = mocker.patch(
        "mrok.cli.commands.agent.dev.console.InspectorApp", return_value=mocked_app
    )
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split("agent dev console -s 41234"),
    )
    assert result.exit_code == 0
    mocked_app_ctor.assert_called_once_with(41234)
    mocked_app.run.assert_called_once()


def test_dev_web(
    mocker: MockerFixture,
):
    mocked_server = mocker.MagicMock()
    mocked_server_ctor = mocker.patch(
        "mrok.cli.commands.agent.dev.web.InspectorServer", return_value=mocked_server
    )
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split("agent dev web -p 9090 -s 41234"),
    )
    assert result.exit_code == 0
    mocked_server_ctor.assert_called_once_with(port=9090, subscriber_port=41234)
    mocked_server.serve.assert_called_once()
