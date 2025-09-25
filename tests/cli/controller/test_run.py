import multiprocessing

from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app
from mrok.controller.app import app as fastapi_app


def test_run(mocker: MockerFixture):
    mocker.patch(
        "mrok.cli.commands.controller.run.get_logging_config",
        return_value={"logging": "config"},
    )
    mocked_app = mocker.MagicMock()
    mocked_standalone_app = mocker.patch(
        "mrok.cli.commands.controller.run.StandaloneApplication", return_value=mocked_app
    )
    runner = CliRunner()
    result = runner.invoke(app, ["controller", "run"])
    assert result.exit_code == 0
    mocked_standalone_app.assert_called_once_with(
        fastapi_app,
        {
            "bind": "127.0.0.1:8000",
            "workers": (multiprocessing.cpu_count() * 2) + 1,
            "worker_class": "uvicorn_worker.UvicornWorker",
            "logconfig_dict": {"logging": "config"},
            "reload": False,
        },
    )
    mocked_app.run.assert_called_once()


def test_run_with_options(mocker: MockerFixture):
    mocker.patch(
        "mrok.cli.commands.controller.run.get_logging_config",
        return_value={"logging": "config"},
    )
    mocked_app = mocker.MagicMock()
    mocked_standalone_app = mocker.patch(
        "mrok.cli.commands.controller.run.StandaloneApplication", return_value=mocked_app
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["controller", "run", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--reload"],
    )
    assert result.exit_code == 0
    mocked_standalone_app.assert_called_once_with(
        fastapi_app,
        {
            "bind": "0.0.0.0:8080",
            "workers": 2,
            "worker_class": "uvicorn_worker.UvicornWorker",
            "logconfig_dict": {"logging": "config"},
            "reload": True,
        },
    )
