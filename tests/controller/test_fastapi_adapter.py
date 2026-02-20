import pytest
from fastapi import HTTPException, status
from pytest_mock import MockerFixture

from mrok.authentication import AuthIdentity
from mrok.controller.dependencies.auth import build_fastapi_auth_dependencies


@pytest.mark.asyncio
async def test_fastapi_adapter(mocker: MockerFixture):
    scope = {
        "type": "http",
        "headers": [(b"authorization", b"Bearer token")],
    }
    identity = AuthIdentity(subject="peter_parker")

    auth_manager = mocker.AsyncMock(return_value=identity)
    dependency = build_fastapi_auth_dependencies(auth_manager)
    request = mocker.MagicMock()
    request.scope = scope
    result = await dependency(request)
    assert result == identity
    auth_manager.assert_called_once_with(scope)


@pytest.mark.asyncio
async def test_fastapi_adapter_401(mocker: MockerFixture):
    auth_manager = mocker.AsyncMock(return_value=None)
    dependency = build_fastapi_auth_dependencies(auth_manager)
    request = mocker.MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        await dependency(request)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Unauthorized"
