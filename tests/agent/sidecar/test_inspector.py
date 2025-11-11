from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from textual.pilot import Pilot
from textual.widgets import DataTable

from mrok.agent.sidecar.inspector import InspectorApp
from tests.conftest import SettingsFactory
from tests.types import SnapCompare


def test_inspector_app(
    mocker: MockerFixture,
    snap_compare: SnapCompare,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=f"http://127.0.0.1:{settings.sidecar.store_port}/requests/",
        json=[
            {
                "method": "GET",
                "path": "/extensions/EXT-1234/instances/INS-1234-0001",
                "raw_path": "/extensions/EXT-1234/instances/INS-1234-0001",
                "query_string": "",
                "request_body": "",
                "request_headers": [["host", "ext-0000-0000.ext.s1.today"]],
                "response_body": '{"detail":"Unauthorized."}',
                "response_headers": [
                    ["date", "Fri, 14 Nov 2025 18:24:42 GMT"],
                    ["server", "uvicorn"],
                    ["content-length", "26"],
                    ["content-type", "application/json"],
                ],
                "status": 401,
                "start": "2025-11-14T13:24:42.439943",
                "duration": 0.00645613670349121,
                "id": 3,
            },
            {
                "method": "GET",
                "path": "/extensions/ext-0000-0000/instances",
                "raw_path": "/extensions/ext-0000-0000/instances",
                "query_string": "limit=50&offset=0",
                "request_body": "",
                "request_headers": [["host", "ext-0000-0000.ext.s1.today"]],
                "response_body": '[{"id":"inst1"},{"id":"inst2"}]',
                "response_headers": [
                    ["date", "Fri, 14 Nov 2025 18:24:34 GMT"],
                    ["server", "uvicorn"],
                    ["content-length", "30"],
                    ["content-type", "application/json"],
                ],
                "status": 200,
                "start": "2025-11-14T13:24:34.838441",
                "duration": 0.00776505470275879,
                "id": 2,
            },
        ],
    )
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)
    assert snap_compare(InspectorApp(), terminal_size=(120, 35))


def test_inspector_app_open_card(
    mocker: MockerFixture,
    snap_compare: SnapCompare,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=f"http://127.0.0.1:{settings.sidecar.store_port}/requests/",
        json=[
            {
                "method": "POST",
                "path": "/extensions/EXT-1234/instances",
                "raw_path": "/extensions/EXT-1234/instances",
                "query_string": "redirect=False",
                "request_body": '{"detail":"Unauthorized."}',
                "request_headers": [["host", "ext-0000-0000.ext.s1.today"]],
                "response_body": '{"id":"inst-1234-0001"}',
                "response_headers": [
                    ["date", "Fri, 14 Nov 2025 18:24:42 GMT"],
                    ["server", "uvicorn"],
                    ["content-length", "23"],
                    ["content-type", "application/json"],
                ],
                "status": 201,
                "start": "2025-11-14T13:24:42.439943",
                "duration": 0.00645613670349121,
                "id": 3,
            },
        ],
    )
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)

    async def run_before(pilot: Pilot):
        await pilot.pause(0.5)
        table = pilot.app.query_one(DataTable)
        await pilot.click(table)
        await pilot.press("enter")

    assert snap_compare(InspectorApp(), terminal_size=(120, 35), run_before=run_before)


def test_inspector_app_empty_card(
    mocker: MockerFixture,
    snap_compare: SnapCompare,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=f"http://127.0.0.1:{settings.sidecar.store_port}/requests/",
        json=[{"id": 1}],
    )
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)

    async def run_before(pilot: Pilot):
        await pilot.pause(0.5)
        table = pilot.app.query_one(DataTable)
        await pilot.click(table)
        await pilot.press("enter")

    assert snap_compare(InspectorApp(), terminal_size=(120, 35), run_before=run_before)


def test_inspector_app_filed_store_connection(
    mocker: MockerFixture,
    snap_compare: SnapCompare,
    settings_factory: SettingsFactory,
    httpx_mock: HTTPXMock,
):
    settings = settings_factory()
    httpx_mock.add_response(
        method="GET",
        url=f"http://127.0.0.1:{settings.sidecar.store_port}/requests/",
        status_code=500,
    )
    mocker.patch("mrok.cli.main.get_settings", return_value=settings)

    assert snap_compare(InspectorApp(), terminal_size=(120, 35))
