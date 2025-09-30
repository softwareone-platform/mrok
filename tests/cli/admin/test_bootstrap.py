import logging
import shlex
import tempfile

import pytest
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app
from mrok.cli.commands.admin.bootstrap import bootstrap
from tests.conftest import SettingsFactory


def test_bootstrap_command(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    logger = logging.getLogger("mrok")
    logger.handlers.clear()
    logger.propagate = True

    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_bootstrap_coro = mocker.MagicMock()
    mock_bootstrap = mocker.MagicMock(return_value=mock_bootstrap_coro)

    mocker.patch("mrok.cli.commands.admin.bootstrap.bootstrap", mock_bootstrap)
    mock_run = mocker.patch(
        "mrok.cli.commands.admin.bootstrap.asyncio.run",
        return_value=({"id": "identity_id"}, {"identity": "json"}),
    )
    runner = CliRunner()

    # Run the command
    with tempfile.NamedTemporaryFile() as f:
        result = runner.invoke(
            app,
            shlex.split(f"admin bootstrap {f.name} --tag tag=tagvalue"),
        )
        f.seek(0)
        json_data = f.read()
        assert json_data == b'{"identity": "json"}'
        assert result.exit_code == 0

    mock_run.assert_called_once_with(mock_bootstrap_coro)
    mock_bootstrap.assert_called_once_with(
        settings,
        False,
        {"tag": "tagvalue"},
    )


@pytest.mark.asyncio
async def test_bootstrap(mocker: MockerFixture, settings_factory: SettingsFactory):
    settings = settings_factory()
    mocked_api = mocker.AsyncMock()
    mocked_api.__aenter__.return_value = mocked_api
    mocked_api_ctor = mocker.patch(
        "mrok.cli.commands.admin.bootstrap.ZitiManagementAPI",
        return_value=mocked_api,
    )
    mocked_cl_api = mocker.AsyncMock()
    mocked_cl_api.__aenter__.return_value = mocked_cl_api
    mocked_cl_api_ctor = mocker.patch(
        "mrok.cli.commands.admin.bootstrap.ZitiClientAPI",
        return_value=mocked_cl_api,
    )
    mocked_bootstrap_identity = mocker.patch("mrok.cli.commands.admin.bootstrap.bootstrap_identity")

    await bootstrap(settings, False, None)
    mocked_bootstrap_identity.assert_awaited_once_with(
        mocked_api,
        mocked_cl_api,
        settings.proxy.identity,
        settings.proxy.mode,
        False,
        None,
    )
    mocked_api_ctor.assert_called_once_with(settings)
    mocked_cl_api_ctor.assert_called_once_with(settings)
