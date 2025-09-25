import json
import shlex
from pathlib import Path

import yaml
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app


def test_openapi(mocker: MockerFixture):
    spec = {"test": "openapi"}
    mocker.patch("mrok.cli.commands.controller.openapi.generate_openapi_spec", return_value=spec)
    mocked_open = mocker.mock_open()
    mocker.patch("mrok.cli.commands.controller.openapi.open", mocked_open)

    runner = CliRunner()
    result = runner.invoke(app, shlex.split("controller openapi"))

    assert result.exit_code == 0
    mocked_open.assert_called_once_with(Path("mrok_openapi_spec.yml"), "w")
    written_data = "".join(call.args[0] for call in mocked_open().write.call_args_list)
    assert written_data == yaml.dump(spec, indent=2)


def test_openapi_custom_output(mocker: MockerFixture):
    spec = {"test": "openapi"}
    mocker.patch("mrok.cli.commands.controller.openapi.generate_openapi_spec", return_value=spec)
    mocked_open = mocker.mock_open()
    mocker.patch("mrok.cli.commands.controller.openapi.open", mocked_open)

    runner = CliRunner()
    result = runner.invoke(app, shlex.split("controller openapi -o openapi.json -f json"))

    assert result.exit_code == 0
    mocked_open.assert_called_once_with(Path("openapi.json"), "w")
    written_data = "".join(call.args[0] for call in mocked_open().write.call_args_list)
    assert written_data == json.dumps(spec, indent=2)
