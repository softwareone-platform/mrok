from unittest.mock import AsyncMock

import pytest
from dynaconf.utils.boxing import DynaBox

from mrok.authentication import AuthIdentity, HTTPAuthManager


def test_setup_backends_raises_when_backend_not_registered(mocker):
    settings = DynaBox({"backends": ["server_404"]})
    mocker.patch(
        "mrok.authentication.manager.get_authentication_backend",
        return_value=None,
    )
    backend1 = mocker.MagicMock()
    backend1.authenticate = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="Backend 'server_404' is not registered."):
        HTTPAuthManager(settings)


def test_setup_backends_with_no_backends():
    settings = DynaBox({"backends": []})
    response = HTTPAuthManager(settings)
    assert response.active_backends == []


@pytest.mark.asyncio
async def test_authenticate_with_at_least_one_backend(mocker):
    settings = DynaBox({"backends": []})

    manager = HTTPAuthManager(settings)

    identity = AuthIdentity(subject="peter_parker")

    backend1 = mocker.MagicMock()
    backend1.authenticate = AsyncMock(return_value=None)

    backend2 = mocker.MagicMock()
    backend2.authenticate = AsyncMock(return_value=identity)

    manager.active_backends = [backend1, backend2]

    result = await manager.authenticate("Bearer token")

    assert result is identity

    backend1.authenticate.assert_awaited_once()
    backend2.authenticate.assert_awaited_once()


@pytest.mark.asyncio
async def test_backends_do_not_authenticate(mocker):
    settings = DynaBox({"backends": []})

    manager = HTTPAuthManager(settings)

    backend1 = mocker.MagicMock()
    backend1.authenticate = AsyncMock(return_value=None)

    manager.active_backends = [backend1]

    result = await manager.authenticate("Bearer token")

    assert result is None

    backend1.authenticate.assert_awaited_once()


@pytest.mark.asyncio
async def test_call_extract_headers(mocker):
    settings = DynaBox({"backends": []})
    manager = HTTPAuthManager(settings)
    manager.authenticate = AsyncMock(return_value="identity")
    scope = {
        "type": "http",
        "headers": [
            (b"authorization", b"Bearer token"),
        ],
    }

    result = await manager(scope)

    manager.authenticate.assert_awaited_once_with("Bearer token")
    assert result == "identity"


@pytest.mark.asyncio
async def test_call_no_headers(mocker):
    settings = DynaBox({"backends": []})
    manager = HTTPAuthManager(settings)
    manager.authenticate = AsyncMock(return_value=None)
    scope = {
        "type": "http",
        "headers": [],
    }

    result = await manager(scope)

    manager.authenticate.assert_awaited_once()
    assert result is None
