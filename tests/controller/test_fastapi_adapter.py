from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status

from mrok.authentication import AuthIdentity
from mrok.authentication.base import AuthenticationError
from mrok.controller.fastapi_auth_adapter import build_fastapi_auth_dependencies


async def test_fastapi_adapter(mocker):
    identity = AuthIdentity(subject="peter_parker")
    auth_manager = AsyncMock()
    auth_manager.authenticate = AsyncMock(return_value=identity)
    dependency = build_fastapi_auth_dependencies(auth_manager)
    request = MagicMock()
    request.scope = {"type": "http"}
    request.headers.get.return_value = "Bearer token"
    result = await dependency(request)
    assert result == identity
    auth_manager.authenticate.assert_called_once_with("Bearer token")


async def test_fastapi_adapter_401(mocker):
    auth_manager = AsyncMock()
    auth_manager.authenticate = AsyncMock(side_effect=AuthenticationError)
    dependency = build_fastapi_auth_dependencies(auth_manager)
    request = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        await dependency(request)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Unauthorized"
