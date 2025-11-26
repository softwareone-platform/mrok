import shlex

import pytest
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from mrok.cli import app
from mrok.cli.commands.admin.list.extensions import get_extensions
from mrok.cli.commands.admin.list.instances import get_instances
from mrok.ziti.constants import MROK_IDENTITY_TYPE_TAG_NAME, MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE
from tests.conftest import SettingsFactory


@pytest.mark.parametrize(
    ("output", "detailed"),
    [
        ("--tsv", ""),
        ("--tsv", "-d"),
        ("", ""),
        ("", "-d"),
    ],
)
def test_list_extensions_command(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    output: str,
    detailed: str,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)

    mock_get = mocker.AsyncMock(
        return_value=[
            {
                "id": "svc",
                "name": "svc",
                "tags": [],
                "configs": [],
                "policies": [],
                "createdAt": "2025-10-13T09:51:06.175Z",
                "updatedAt": "2025-10-13T09:51:06.175Z",
            },
        ],
    )
    mocker.patch(
        "mrok.cli.commands.admin.list.extensions.get_extensions",
        new=mock_get,
    )
    runner = CliRunner()

    # Run the command
    result = runner.invoke(
        app,
        shlex.split(f"admin list extensions {output} {detailed}"),
    )
    assert result.exit_code == 0
    mock_get.assert_called_once_with(settings, detailed == "-d", None)


def test_list_extensions_command_with_tag(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)

    mock_get = mocker.AsyncMock(return_value=[])
    mocker.patch(
        "mrok.cli.commands.admin.list.extensions.get_extensions",
        new=mock_get,
    )

    runner = CliRunner()
    # Run the command
    result = runner.invoke(
        app,
        shlex.split("admin list extensions -t mytag=v1"),
    )

    assert "No extensions found" in result.output
    mock_get.assert_called_once_with(settings, False, ["mytag=v1"])


@pytest.mark.asyncio
async def test_list_extensions(settings_factory: SettingsFactory, httpx_mock: HTTPXMock):
    settings = settings_factory()
    url = f"{settings.ziti.api.management}/edge/management/v1/services"

    httpx_mock.add_response(
        method="GET",
        url=f"{url}?limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 1, "limit": 5, "offset": 0}},
            "data": [{"id": "svc", "name": "svc"}],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{url}/svc/configs?limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 1, "limit": 5, "offset": 0}},
            "data": [{"id": "cnfg", "name": "config"}],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{url}/svc/service-policies?limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 1, "limit": 5, "offset": 0}},
            "data": [{"id": "plc", "name": "svc-policy"}],
        },
    )

    extensions = await get_extensions(settings, True)
    assert len(extensions) == 1
    assert extensions[0] == {
        "id": "svc",
        "name": "svc",
        "configs": [{"id": "cnfg", "name": "config"}],
        "policies": [{"id": "plc", "name": "svc-policy"}],
    }


@pytest.mark.asyncio
async def test_list_extensions_with_tag(settings_factory: SettingsFactory, httpx_mock: HTTPXMock):
    settings = settings_factory()
    url = f"{settings.ziti.api.management}/edge/management/v1/services"

    httpx_mock.add_response(
        method="GET",
        url=f'{url}?filter=tags.mytag="v1"&limit=5&offset=0',
        json={
            "meta": {"pagination": {"totalCount": 1, "limit": 5, "offset": 0}},
            "data": [{"id": "svc", "name": "svc", "tags": [{"mytag": "v1"}]}],
        },
    )

    extensions = await get_extensions(settings, False, ["mytag=v1"])
    assert len(extensions) == 1
    assert extensions[0] == {
        "id": "svc",
        "name": "svc",
        "tags": [{"mytag": "v1"}],
    }


@pytest.mark.parametrize(
    ("output", "detailed"),
    [
        ("--tsv", ""),
        ("--tsv", "-d"),
        ("", ""),
        ("", "-d"),
    ],
)
def test_list_instances_command(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    output: str,
    detailed: str,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    mock_get = mocker.patch(
        "mrok.cli.commands.admin.list.instances.get_instances",
        return_value=[
            {
                "id": "idt",
                "name": "idt",
                "tags": [],
                "services": [],
                "policies": [],
                "hasEdgeRouterConnection": False,
                "createdAt": "2025-10-13T09:51:06.175Z",
                "updatedAt": "2025-10-13T09:51:06.175Z",
            },
        ],
    )

    runner = CliRunner()
    # Run the command
    result = runner.invoke(
        app,
        shlex.split(f"admin list instances {output} {detailed}"),
    )
    assert result.exit_code == 0
    mock_get.assert_called_once_with(settings, detailed == "-d", None, None, False)


def test_list_instances_command_with_tag(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)

    mock_get = mocker.AsyncMock(return_value=[])
    mocker.patch(
        "mrok.cli.commands.admin.list.instances.get_instances",
        new=mock_get,
    )

    runner = CliRunner()
    # Run the command
    result = runner.invoke(
        app,
        shlex.split("admin list instances -t mytag=v1"),
    )

    assert "No instances found" in result.output
    mock_get.assert_called_once_with(settings, False, None, ["mytag=v1"], False)


@pytest.mark.asyncio
async def test_list_instances_with_extension_filter(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    tag_filter = f'tags.{MROK_IDENTITY_TYPE_TAG_NAME}="{MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE}"'
    url = f"{settings.ziti.api.management}/edge/management/v1/identities"

    httpx_mock.add_response(
        method="GET",
        url=f"{url}?filter={tag_filter}&limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 1, "limit": 5, "offset": 0}},
            "data": [{"id": "idt", "name": "identity"}],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{url}/idt/services?limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 1, "limit": 5, "offset": 0}},
            "data": [{"id": "svc", "name": "svc"}],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{url}/idt/service-policies?limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 1, "limit": 5, "offset": 0}},
            "data": [{"id": "plc", "name": "svc-policy"}],
        },
    )

    instances = await get_instances(settings, False, "svc")
    assert len(instances) == 1
    assert instances[0] == {
        "id": "idt",
        "name": "identity",
        "services": [{"id": "svc", "name": "svc"}],
        "policies": [{"id": "plc", "name": "svc-policy"}],
    }


@pytest.mark.asyncio
async def test_list_instances_with_online_only_filter(
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    tag_filter = f'tags.{MROK_IDENTITY_TYPE_TAG_NAME}="{MROK_IDENTITY_TYPE_TAG_VALUE_INSTANCE}"'
    url = f"{settings.ziti.api.management}/edge/management/v1/identities"

    httpx_mock.add_response(
        method="GET",
        url=f"{url}?filter={tag_filter}&limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 2, "limit": 5, "offset": 0}},
            "data": [
                {"id": "idt", "name": "identity", "hasEdgeRouterConnection": True},
                {"id": "idt2", "name": "identity", "hasEdgeRouterConnection": False},
            ],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{url}/idt/services?limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 1, "limit": 5, "offset": 0}},
            "data": [{"id": "svc", "name": "svc"}],
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{url}/idt/service-policies?limit=5&offset=0",
        json={
            "meta": {"pagination": {"totalCount": 1, "limit": 5, "offset": 0}},
            "data": [{"id": "plc", "name": "svc-policy"}],
        },
    )

    instances = await get_instances(settings, False, "svc", online_only=True)
    assert len(instances) == 1
    assert instances[0] == {
        "id": "idt",
        "name": "identity",
        "services": [{"id": "svc", "name": "svc"}],
        "policies": [{"id": "plc", "name": "svc-policy"}],
        "hasEdgeRouterConnection": True,
    }
