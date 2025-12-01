import shlex

import pytest
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app
from mrok.cli.commands.admin.unregister.extensions import do_unregister as do_unregister_extension
from mrok.cli.commands.admin.unregister.instances import do_unregister as do_unregister_instance
from tests.conftest import SettingsFactory


def test_unregister_extension_command(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_unregister_coro = mocker.MagicMock()
    mock_unregister = mocker.MagicMock(return_value=mock_unregister_coro)

    mocker.patch("mrok.cli.commands.admin.unregister.extensions.do_unregister", mock_unregister)
    mock_run = mocker.patch("mrok.cli.commands.admin.unregister.extensions.asyncio.run")
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split("admin unregister extension EXT-1234-5678"),
    )
    assert result.exit_code == 0
    mock_run.assert_called_once_with(mock_unregister_coro)

    mock_unregister.assert_called_once_with(
        settings,
        "EXT-1234-5678",
    )


def test_unregister_extension_command_invalid_extension_id(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_unregister_coro = mocker.MagicMock()
    mock_unregister = mocker.MagicMock(return_value=mock_unregister_coro)

    mocker.patch("mrok.cli.commands.admin.unregister.extensions.do_unregister", mock_unregister)
    mocker.patch("mrok.cli.commands.admin.unregister.extensions.asyncio.run")
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split("admin unregister extension EXT-1234"),
    )
    assert result.exit_code == 2
    assert "Invalid value for 'EXTENSION_ID': ext_id must match EXT-xxxx-yyyy" in result.stderr


@pytest.mark.asyncio
async def test_do_unregister_extension(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.__aenter__.return_value = mocked_api
    mocked_api_ctor = mocker.patch(
        "mrok.cli.commands.admin.unregister.extensions.ZitiManagementAPI",
        return_value=mocked_api,
    )
    mocked_unregister_service = mocker.patch(
        "mrok.cli.commands.admin.unregister.extensions.unregister_service"
    )

    await do_unregister_extension(settings, "EXT-1234")
    mocked_unregister_service.assert_awaited_once_with(
        settings,
        mocked_api,
        "EXT-1234",
    )
    mocked_api_ctor.assert_called_once_with(settings)


# ===========


def test_unregister_instance_command(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_unregister_coro = mocker.MagicMock()
    mock_unregister = mocker.MagicMock(return_value=mock_unregister_coro)

    mocker.patch("mrok.cli.commands.admin.unregister.instances.do_unregister", mock_unregister)
    mock_run = mocker.patch("mrok.cli.commands.admin.unregister.instances.asyncio.run")
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split("admin unregister instance EXT-1234-5678 INS-1234-5678-0001"),
    )
    assert result.exit_code == 0
    mock_run.assert_called_once_with(mock_unregister_coro)

    mock_unregister.assert_called_once_with(
        settings,
        "EXT-1234-5678",
        "INS-1234-5678-0001",
    )


def test_unregister_instance_command_invalid_extension_id(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_unregister_coro = mocker.MagicMock()
    mock_unregister = mocker.MagicMock(return_value=mock_unregister_coro)

    mocker.patch("mrok.cli.commands.admin.unregister.instances.do_unregister", mock_unregister)
    mocker.patch("mrok.cli.commands.admin.unregister.instances.asyncio.run")
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split("admin unregister instance EXT-1234 INS-1234-0001"),
    )
    assert result.exit_code == 2
    assert "Invalid value for 'EXTENSION_ID': ext_id must match EXT-xxxx-yyyy" in result.stderr


@pytest.mark.asyncio
async def test_do_unregister_instance(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.__aenter__.return_value = mocked_api
    mocked_api_ctor = mocker.patch(
        "mrok.cli.commands.admin.unregister.instances.ZitiManagementAPI",
        return_value=mocked_api,
    )
    mocked_unregister_service = mocker.patch(
        "mrok.cli.commands.admin.unregister.instances.unregister_identity"
    )

    await do_unregister_instance(settings, "EXT-1234", "INS-1234-0001")
    mocked_unregister_service.assert_awaited_once_with(
        settings,
        mocked_api,
        "EXT-1234",
        "INS-1234-0001",
    )
    mocked_api_ctor.assert_called_once_with(settings)
