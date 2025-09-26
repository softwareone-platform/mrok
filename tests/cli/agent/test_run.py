import shlex

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
        shlex.split("agent run asgi my:app ext-1234-5678 ins-1234-5678-0001.json -w 2 --reload"),
    )
    assert result.exit_code == 0
    mocked_ziticorn.assert_called_once_with(
        "my:app", "ext-1234-5678", "ins-1234-5678-0001.json", workers=2, reload=True
    )
