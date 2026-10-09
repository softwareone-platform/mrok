import json

import pytest
from pytest_mock import MockerFixture

from mrok.frontend.middleware import HealthCheckMiddleware, TargetMiddleware
from mrok.logging import request_target


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


@pytest.mark.asyncio
async def test_target_middleware_sets_target(mocker: MockerFixture):
    mocker.patch("mrok.frontend.utils.get_frontend_domain", return_value=".extdomain")
    seen: list[str | None] = []
    m_app = mocker.AsyncMock(side_effect=lambda *args: seen.append(request_target.get()))
    m_receive = mocker.AsyncMock()
    m_send = mocker.AsyncMock()
    middleware = TargetMiddleware(m_app)
    scope = {
        "type": "http",
        "path": "/",
        "headers": [(b"host", b"EXT-1234-5678.extdomain:8000")],
    }

    await middleware(scope, m_receive, m_send)

    m_app.assert_awaited_once_with(scope, m_receive, m_send)
    assert seen == ["ext-1234-5678"]
    assert request_target.get() is None


@pytest.mark.asyncio
async def test_target_middleware_without_target(mocker: MockerFixture):
    mocker.patch("mrok.frontend.utils.get_frontend_domain", return_value=".extdomain")
    seen: list[str | None] = []
    m_app = mocker.AsyncMock(side_effect=lambda *args: seen.append(request_target.get()))
    m_receive = mocker.AsyncMock()
    m_send = mocker.AsyncMock()
    middleware = TargetMiddleware(m_app)
    scope = {"type": "http", "path": "/", "headers": [(b"host", b"127.0.0.1")]}

    await middleware(scope, m_receive, m_send)

    m_app.assert_awaited_once_with(scope, m_receive, m_send)
    assert seen == [None]
