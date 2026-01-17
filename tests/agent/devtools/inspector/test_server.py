import pytest
from pytest_mock import MockerFixture

from mrok.agent.devtools.inspector.server import InspectorServer


def test_server_init():
    server = InspectorServer(port=8901, subscriber_port=18237)
    assert server.command == "python -m mrok.agent.devtools.inspector -p 18237"
    assert server.port == 8901


@pytest.mark.asyncio
async def test_server_on_startup(mocker: MockerFixture):
    console = mocker.MagicMock()
    server = InspectorServer(port=8901, subscriber_port=18237)
    server.console = console

    await server.on_startup(mocker.MagicMock())

    assert console.print.mock_calls[0].args[0] == (
        f"Serving mrok inspector web app on {server.public_url} "
        f"(subscriber port {server.subscriber_port})"
    )
    assert console.print.mock_calls[1].args[0] == "\n[cyan]Press Ctrl+C to quit"
