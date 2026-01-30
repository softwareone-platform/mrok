import json

import pytest
from pytest_mock import MockerFixture

from mrok.frontend.middleware import HealthCheckMiddleware


@pytest.mark.asyncio
async def test_healthcheck(
    mocker: MockerFixture,
):
    m_app = mocker.AsyncMock()
    m_receive = mocker.AsyncMock()
    m_send = mocker.AsyncMock()
    middleware = HealthCheckMiddleware(m_app)

    await middleware(
        {"type": "http", "path": "/healthcheck", "headers": [(b"host", b"127.0.0.1")]},
        m_receive,
        m_send,
    )

    assert m_send.mock_calls[0].args[0] == {
        "type": "http.response.start",
        "status": 200,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    }

    assert m_send.mock_calls[1].args[0] == {
        "type": "http.response.body",
        "body": json.dumps({"status": "healthy"}).encode("utf-8"),
    }


@pytest.mark.asyncio
async def test_healthcheck_passtrhough(
    mocker: MockerFixture,
):
    m_app = mocker.AsyncMock()
    m_receive = mocker.AsyncMock()
    m_send = mocker.AsyncMock()
    mocker.patch("mrok.frontend.utils.get_frontend_domain", return_value=".extdomain")
    middleware = HealthCheckMiddleware(m_app)

    scope = {
        "type": "http",
        "path": "/healthcheck",
        "headers": [(b"host", b"ext-1234-5678.extdomain")],
    }

    await middleware(
        scope,
        m_receive,
        m_send,
    )

    m_app.assert_awaited_once_with(scope, m_receive, m_send)
