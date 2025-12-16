import pytest
from pytest_mock import MockerFixture

from mrok.frontend.app import FrontendProxyApp
from mrok.proxy.exceptions import InvalidTargetError


def test_init(
    mocker: MockerFixture,
):
    m_async_pool_ctor = mocker.patch("mrok.frontend.app.AsyncConnectionPool")
    m_ziti_backend = mocker.MagicMock()
    m_ziti_backend_ctor = mocker.patch(
        "mrok.frontend.app.AIOZitiNetworkBackend", return_value=m_ziti_backend
    )
    FrontendProxyApp(
        "my-identity-file",
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
        network_backend=m_ziti_backend,
    )
    m_ziti_backend_ctor.assert_called_once_with("my-identity-file")


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ((b"x-forwarded-host", b"ext-9284-9038.extdomain"), "ext-9284-9038"),
        ((b"host", b"ext-9284-9038.extdomain"), "ext-9284-9038"),
        ((b"x-forwarded-host", b"eXt-9284-9038.extdomain"), "ext-9284-9038"),
        ((b"host", b"EXT-9284-9038.extdomain"), "ext-9284-9038"),
        ((b"x-forwarded-host", b"ins-9284-9038-0001.extdomain"), "ins-9284-9038-0001"),
        ((b"host", b"ins-9284-9038-0001.extdomain"), "ins-9284-9038-0001"),
        ((b"x-forwarded-host", b"inS-9284-9038-0001.extdomain"), "ins-9284-9038-0001"),
        ((b"host", b"INS-9284-9038-0001.extdomain"), "ins-9284-9038-0001"),
        ((b"x-forwarded-host", b"ext-9284-9038.extdomain:1234"), "ext-9284-9038"),
        ((b"host", b"ext-9284-9038.extdomain:1234"), "ext-9284-9038"),
        ((b"x-forwarded-host", b"eXt-9284-9038.extdomain:1234"), "ext-9284-9038"),
        ((b"host", b"EXT-9284-9038.extdomain:1234"), "ext-9284-9038"),
        ((b"x-forwarded-host", b"ins-9284-9038-0001.extdomain:1234"), "ins-9284-9038-0001"),
        ((b"host", b"ins-9284-9038-0001.extdomain:1234"), "ins-9284-9038-0001"),
        ((b"x-forwarded-host", b"inS-9284-9038-0001.extdomain:1234"), "ins-9284-9038-0001"),
        ((b"host", b"INS-9284-9038-0001.extdomain:1234"), "ins-9284-9038-0001"),
    ],
)
def test_get_upstream_base_url(
    mocker: MockerFixture,
    header: tuple[bytes, bytes],
    expected: str,
):
    mocker.patch.object(FrontendProxyApp, "_get_proxy_domain", return_value=".extdomain")

    app = FrontendProxyApp("my-identity")
    assert app.get_upstream_base_url({"headers": [header]}) == f"http://{expected}"


@pytest.mark.parametrize(
    "header",
    [
        (b"x-forwarded-host", b"ext-9284.extdomain"),
        (b"host", b"ext-9284.extdomain"),
        (b"x-forwarded-host", b"ins-9292-9292-1.extdomain"),
        (b"host", b"ins-9292-9292-1.extdomain"),
        (b"x-forwarded-host", b"whatever.extdomain"),
        (b"host", b"whatever.extdomain"),
        (b"x-forwarded-host", b"ext-9284-9038.otherdomain"),
        (b"host", b"ext-9284-9038.otherdomain"),
        (b"x-forwarded-host", b"ins-9284-9038-0001.otherdomain"),
        (b"host", b"ins-9284-9038-0001.otherdomain"),
    ],
)
def test_get_upstream_base_url_invalid_target(
    mocker: MockerFixture,
    header: tuple[bytes, bytes],
):
    mocker.patch.object(FrontendProxyApp, "_get_proxy_domain", return_value=".extdomain")

    app = FrontendProxyApp("my-identity")
    with pytest.raises(InvalidTargetError):
        app.get_upstream_base_url({"headers": [header]})
