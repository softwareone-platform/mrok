import pytest
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app, main, run


def test_help_show_banner(mocker: MockerFixture):
    mocked_show = mocker.patch("mrok.cli.main.show_banner")
    runner = CliRunner()
    # Run the command
    runner.invoke(
        app,
        ["--help"],
    )
    mocked_show.assert_called_once()


def test_run(mocker: MockerFixture):
    app = mocker.MagicMock()
    mocker.patch.object(main, "app", app)
    run()
    app.assert_called_once()


def test_run_exception(mocker: MockerFixture):
    app = mocker.MagicMock()
    err_console = mocker.MagicMock()
    app.side_effect = Exception("whatever")
    mocker.patch.object(main, "app", app)
    mocker.patch.object(main, "err_console", err_console)
    with pytest.raises(SystemExit) as exc:
        run()
    assert exc.value.code == -1
    err_console.print.assert_called_once_with("[bold red]Error:[/bold red] whatever")
