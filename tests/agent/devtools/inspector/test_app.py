import asyncio

import pytest
from pytest_mock import MockerFixture
from textual.pilot import Pilot

from mrok.agent.devtools.inspector.app import MIN_COLS, MIN_ROWS, InspectorApp, module_main
from tests.types import ResponseEventFactory, SnapCompare, StatusEventFactory, ZMQPublisher


def test_app_get_headers(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, response_event_factory())
        await asyncio.to_thread(s.send_json, status_event_factory())
        await pilot.click(offset=(5, 9))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_get_payload(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, response_event_factory())
        await asyncio.to_thread(s.send_json, status_event_factory())
        await pilot.click(offset=(5, 9))
        await pilot.click(offset=(13, 20))
        await pilot.click(offset=(2, 22))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_get_preview(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, response_event_factory())
        await asyncio.to_thread(s.send_json, status_event_factory())
        await pilot.click(offset=(5, 9))
        await pilot.click(offset=(22, 20))
        await pilot.click(offset=(2, 22))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_get_raw_response(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher

    status = status_event_factory(process_cpu=32.2, process_mem=100)

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, status)
        await asyncio.to_thread(s.send_json, response_event_factory())
        await pilot.click(offset=(5, 9))
        await pilot.click(offset=(31, 20))
        await pilot.click(offset=(2, 22))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_get_preview_binary(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher
    response_event = response_event_factory(
        response_headers={"content-type": "application/octet-stream"},
        response_body=b"blablabla",
    )

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, response_event)
        await asyncio.to_thread(s.send_json, status_event_factory())
        await pilot.click(offset=(5, 9))
        await pilot.click(offset=(22, 20))
        await pilot.click(offset=(2, 22))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_get_raw_response_binary(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher

    response_event = response_event_factory(
        response_headers={"content-type": "application/octet-stream"},
        response_body=b"blablabla",
    )

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, status_event_factory())
        await asyncio.to_thread(s.send_json, response_event)
        await pilot.click(offset=(5, 9))
        await pilot.click(offset=(31, 20))
        await pilot.click(offset=(2, 22))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_post_headers(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher

    response_event = response_event_factory(
        method="POST",
        request_headers={
            "accept": "application/json",
            "content-type": "application/json",
        },
        request_body=b'{"request": "body"}',
    )

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, status_event_factory())
        await asyncio.to_thread(s.send_json, response_event)
        await pilot.click(offset=(5, 9))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_post_json_body(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher

    response_event = response_event_factory(
        method="POST",
        request_headers={
            "accept": "application/json",
            "content-type": "application/json",
        },
        request_body=b'{"request": "body"}',
    )

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, status_event_factory())
        await asyncio.to_thread(s.send_json, response_event)
        await pilot.click(offset=(5, 9))
        await pilot.click(offset=(13, 20))
        await pilot.click(offset=(2, 22))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_post_preview_multipart(
    multipart_body: tuple[str, bytes],
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher
    boundary, body = multipart_body

    response_event = response_event_factory(
        method="POST",
        request_headers={
            "accept": "application/json",
            "content-type": f"multipart/form-data; boundary={boundary}",
        },
        request_body=body,
    )

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, status_event_factory())
        await asyncio.to_thread(s.send_json, response_event)
        await pilot.click(offset=(5, 9))
        await pilot.click(offset=(13, 20))
        await pilot.click(offset=(2, 22))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_post_preview_body_truncated(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher

    response_event = response_event_factory(
        method="POST",
        request_headers={
            "accept": "application/json",
            "content-type": "application/octet-stream",
        },
        request_body=b"These are a lot of random bytes",
        request_truncated=True,
    )

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, status_event_factory())
        await asyncio.to_thread(s.send_json, response_event)
        await pilot.click(offset=(5, 9))
        await pilot.click(offset=(13, 20))
        await pilot.click(offset=(2, 22))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_delete_headers(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
):
    s, port = zmq_publisher

    response_event = response_event_factory(
        method="DELETE",
    )

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, status_event_factory())
        await asyncio.to_thread(s.send_json, response_event)
        await pilot.click(offset=(5, 9))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


@pytest.mark.parametrize(
    "response_status",
    [400, 500],
)
def test_app_non_200_headers(
    response_event_factory: ResponseEventFactory,
    status_event_factory: StatusEventFactory,
    zmq_publisher: ZMQPublisher,
    snap_compare: SnapCompare,
    response_status: int,
):
    s, port = zmq_publisher

    response_event = response_event_factory(
        method="POST", request_querystring=b"foo=bar&goo=1", response_status=response_status
    )

    async def run_before(pilot: Pilot):
        await asyncio.to_thread(s.send_json, status_event_factory())
        await asyncio.to_thread(s.send_json, response_event)
        await pilot.click(offset=(5, 9))

    assert snap_compare(
        InspectorApp(port), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


def test_app_hide_metrics(
    snap_compare: SnapCompare,
):
    async def run_before(pilot: Pilot):
        await pilot.press("m")

    assert snap_compare(
        InspectorApp(2333), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS)
    )


@pytest.mark.parametrize(
    ("w", "h"),
    [
        (1, 0),
        (0, 1),
        (1, 1),
    ],
)
def test_app_terminal_too_small(
    snap_compare: SnapCompare,
    w: int,
    h: int,
):
    assert snap_compare(InspectorApp(9332), terminal_size=(MIN_COLS - w, MIN_ROWS - h))


def test_app_terminal_too_small_dismiss(
    snap_compare: SnapCompare,
):
    async def run_before(pilot: Pilot):
        await pilot.click("#dismiss")

    assert snap_compare(
        InspectorApp(9332), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS - 15)
    )


def test_app_terminal_too_small_resize_auto_dismiss(
    snap_compare: SnapCompare,
):
    async def run_before(pilot: Pilot):
        await pilot.resize_terminal(MIN_COLS, MIN_ROWS)

    assert snap_compare(
        InspectorApp(9332), run_before=run_before, terminal_size=(MIN_COLS, MIN_ROWS - 15)
    )


@pytest.mark.parametrize(
    ("argv", "expected_port"),
    [
        ([], 50001),
        (["-p", "4949"], 4949),
        (["--subscriber-port", "7777"], 7777),
    ],
)
def test_module_main(
    mocker: MockerFixture,
    argv: list,
    expected_port: int,
):
    m_app = mocker.MagicMock()
    m_ctor = mocker.patch("mrok.agent.devtools.inspector.app.InspectorApp", return_value=m_app)
    module_main(argv)
    m_ctor.assert_called_once_with(expected_port)
    m_app.run.assert_called_once()
