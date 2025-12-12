import shlex
import tempfile

import pytest
from pytest_mock import MockerFixture
from typer import BadParameter
from typer.testing import CliRunner

from mrok.cli import app
from mrok.cli.commands.admin.register.extensions import do_register as do_register_extension
from mrok.cli.commands.admin.register.instances import do_register as do_register_instance
from mrok.cli.commands.admin.utils import parse_tags
from tests.conftest import SettingsFactory


def test_register_extension_command(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_register_coro = mocker.MagicMock()
    mock_register = mocker.MagicMock(return_value=mock_register_coro)

    mocker.patch("mrok.cli.commands.admin.register.extensions.do_register", mock_register)
    mock_run = mocker.patch("mrok.cli.commands.admin.register.extensions.asyncio.run")
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split("admin register extension EXT-1234-5678 --tag tag=tagvalue"),
    )
    assert result.exit_code == 0
    mock_run.assert_called_once_with(mock_register_coro)

    mock_register.assert_called_once_with(
        settings,
        "EXT-1234-5678",
        ["tag=tagvalue"],
    )


def test_register_extension_command_invalid_extension_id(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_register_coro = mocker.MagicMock()
    mock_register = mocker.MagicMock(return_value=mock_register_coro)

    mocker.patch("mrok.cli.commands.admin.register.extensions.do_register", mock_register)
    mocker.patch("mrok.cli.commands.admin.register.extensions.asyncio.run")
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split("admin register extension EXT-1234 --tag tag=tagvalue"),
    )
    assert result.exit_code == 2
    assert "Invalid value for 'EXTENSION_ID': it must match EXT-xxxx-yyyy" in result.stderr


@pytest.mark.asyncio
async def test_do_register_extension(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.__aenter__.return_value = mocked_api
    mocked_api_ctor = mocker.patch(
        "mrok.cli.commands.admin.register.extensions.ZitiManagementAPI",
        return_value=mocked_api,
    )
    mocked_register_service = mocker.patch(
        "mrok.cli.commands.admin.register.extensions.register_service"
    )

    await do_register_extension(settings, "EXT-1234", ["tag=value"])
    mocked_register_service.assert_awaited_once_with(
        settings, mocked_api, "EXT-1234", tags={"tag": "value"}
    )
    mocked_api_ctor.assert_called_once_with(settings)


def test_register_instance_command(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_register_coro = mocker.MagicMock()
    mock_register = mocker.MagicMock(return_value=mock_register_coro)

    mocker.patch("mrok.cli.commands.admin.register.instances.do_register", mock_register)
    mock_run = mocker.patch(
        "mrok.cli.commands.admin.register.instances.asyncio.run",
        return_value=({"id": "identity_id"}, {"identity": "json"}),
    )
    runner = CliRunner()
    with tempfile.NamedTemporaryFile() as f:
        # Run the command
        result = runner.invoke(
            app,
            shlex.split(
                "admin register instance EXT-1234-5678 "
                f"INS-1234-5678-0001 {f.name} --tag tag=tagvalue"
            ),
        )
        f.seek(0)
        json_data = f.read()
        assert json_data == b'{"identity": "json"}'
        assert result.exit_code == 0

    mock_run.assert_called_once_with(mock_register_coro)

    mock_register.assert_called_once_with(
        settings,
        "EXT-1234-5678",
        "INS-1234-5678-0001",
        ["tag=tagvalue"],
    )


def test_register_instance_command_invalid_extension_id(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_register_coro = mocker.MagicMock()
    mock_register = mocker.MagicMock(return_value=mock_register_coro)

    mocker.patch("mrok.cli.commands.admin.register.instances.do_register", mock_register)
    mocker.patch("mrok.cli.commands.admin.register.instances.asyncio.run")
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split(
            "admin register instance EXT-1234 INS-1234-0001 my-file.json --tag tag=tagvalue",
        ),
    )
    assert result.exit_code == 2
    assert "Invalid value for 'EXTENSION_ID': it must match EXT-xxxx-yyyy" in result.stderr


@pytest.mark.asyncio
async def test_do_register_instance(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_mgmt_api = mocker.AsyncMock()
    mocked_mgmt_api.__aenter__.return_value = mocked_mgmt_api
    mocked_mgmt_api_ctor = mocker.patch(
        "mrok.cli.commands.admin.register.instances.ZitiManagementAPI",
        return_value=mocked_mgmt_api,
    )
    mocked_cli_api = mocker.AsyncMock()
    mocked_cli_api.__aenter__.return_value = mocked_cli_api
    mocked_cli_api_ctor = mocker.patch(
        "mrok.cli.commands.admin.register.instances.ZitiClientAPI",
        return_value=mocked_cli_api,
    )
    mocked_register_instance = mocker.patch(
        "mrok.cli.commands.admin.register.instances.register_identity",
    )

    await do_register_instance(settings, "EXT-1234", "INS-1234-0001", ["tag=value"])
    mocked_register_instance.assert_awaited_once_with(
        settings,
        mocked_mgmt_api,
        mocked_cli_api,
        "EXT-1234",
        "INS-1234-0001",
        tags={"tag": "value"},
    )
    mocked_mgmt_api_ctor.assert_called_once_with(settings)
    mocked_cli_api_ctor.assert_called_once_with(settings)


def test_parse_tags():
    assert parse_tags(
        [
            "str=value",
            "true=true",
            "false=false",
            "null=",
        ]
    ) == {
        "str": "value",
        "true": True,
        "false": False,
        "null": None,
    }


@pytest.mark.parametrize("tags_list", [None, []])
def test_parse_tags_no_tags(tags_list):
    assert parse_tags(tags_list) is None


def test_parse_tags_invalid():
    with pytest.raises(BadParameter) as cv:
        parse_tags(["blabla"])
    assert str(cv.value) == "Invalid format 'blabla', expected key=value"
