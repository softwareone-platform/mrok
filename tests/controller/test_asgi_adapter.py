from unittest.mock import AsyncMock

import pytest

from mrok.authentication import AuthIdentity
from mrok.frontend.middleware import ASGIAuthenticationMiddleware


@pytest.mark.asyncio
async def test_auth_success_sets_identity(mocker):
    identity = AuthIdentity(subject="peter_parker")

    auth_manager = AsyncMock(return_value=identity)

    asgi_app = AsyncMock(name="mock_asgi_app")
    scope = {"type": "http"}
    receive = AsyncMock(name="mock_receive")
    send = AsyncMock(name="mock_send")
    middleware = ASGIAuthenticationMiddleware(
        asgi_app,
        auth_manager=auth_manager,
    )
    await middleware(scope, receive, send)
    auth_manager.assert_awaited_once_with(scope)
    assert scope["identity"] is not None

    asgi_app.assert_awaited_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_auth_no_identity(mocker):
    auth_manager = AsyncMock(return_value=None)

    asgi_app = AsyncMock(name="mock_asgi_app")
    scope = {"type": "http"}
    receive = AsyncMock(name="mock_receive")
    send = AsyncMock(name="mock_send")
    middleware = ASGIAuthenticationMiddleware(
        asgi_app,
        auth_manager=auth_manager,
    )
    await middleware(scope, receive, send)
    auth_manager.assert_awaited_once_with(scope)
    assert "identity" not in scope
    asgi_app.assert_awaited_once_with(scope, receive, send)
