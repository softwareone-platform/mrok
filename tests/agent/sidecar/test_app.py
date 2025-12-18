import pytest
from pytest_mock import MockerFixture

from mrok.agent.sidecar.app import SidecarProxyApp


@pytest.mark.parametrize(
    ("target", "addr"),
    [
        ("127.0.0.1:1234", "127.0.0.1:1234"),
        (":8282", "127.0.0.1:8282"),
        (("localhost", 1838), "localhost:1838"),
    ],
)
def test_init(
    mocker: MockerFixture,
    target: str | tuple[str, int],
    addr: str,
):
    m_async_pool_ctor = mocker.patch("mrok.agent.sidecar.app.AsyncConnectionPool")
    app = SidecarProxyApp(
        target,
        max_connections=5000,
        max_keepalive_connections=5,
        keepalive_expiry=60,
        retries=1,
    )

    m_async_pool_ctor.assert_called_once_with(
        max_connections=5000,
        max_keepalive_connections=5,
        keepalive_expiry=60,
        retries=1,
    )

    assert app._target_type == "tcp"
    assert app._target_address == addr


def test_init_uds(
    mocker: MockerFixture,
):
    m_async_pool_ctor = mocker.patch("mrok.agent.sidecar.app.AsyncConnectionPool")
    app = SidecarProxyApp(
        "/path/to/proxy.sock",
        max_connections=5000,
        max_keepalive_connections=5,
        keepalive_expiry=60,
        retries=1,
    )

    m_async_pool_ctor.assert_called_once_with(
        max_connections=5000,
        max_keepalive_connections=5,
        keepalive_expiry=60,
        retries=1,
        uds="/path/to/proxy.sock",
    )

    assert app._target_type == "unix"
    assert app._target_address == "/path/to/proxy.sock"


@pytest.mark.parametrize(
    "target",
    [
        ("a",),
        ("a", "b", "c"),
    ],
)
def test_init_invalid_target(
    mocker: MockerFixture,
    target: tuple,
):
    with pytest.raises(Exception) as cv:
        SidecarProxyApp(
            target,
            max_connections=5000,
            max_keepalive_connections=5,
            keepalive_expiry=60,
            retries=1,
        )
    assert str(cv.value) == f"Invalid target address: {target}"


def test_get_upstream_base_url_tcp():
    app = SidecarProxyApp(
        "1.2.2.3:8000",
        max_connections=5000,
        max_keepalive_connections=5,
        keepalive_expiry=60,
        retries=1,
    )
    assert app.get_upstream_base_url({}) == "http://1.2.2.3:8000"


def test_get_upstream_base_url_unix():
    app = SidecarProxyApp(
        "/path/to/proxy.sock",
        max_connections=5000,
        max_keepalive_connections=5,
        keepalive_expiry=60,
        retries=1,
    )
    assert app.get_upstream_base_url({}) == "http://localhost"
