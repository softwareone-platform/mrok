import pytest
from jinja2 import Template
from pytest_mock import MockerFixture

from mrok.frontend.app import FrontendProxyApp
from mrok.proxy.app import ProxyAppBase
from mrok.proxy.exceptions import InvalidTargetError
from tests.types import SettingsFactory


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
    mocker.patch("mrok.frontend.utils.get_frontend_domain", return_value=".extdomain")

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
    mocker.patch("mrok.frontend.utils.get_frontend_domain", return_value=".extdomain")

    app = FrontendProxyApp("my-identity")
    with pytest.raises(InvalidTargetError):
        app.get_upstream_base_url({"headers": [header]})


@pytest.mark.parametrize(
    "accept_header",
    [
        "text/html, application/json",
        "text/html, application/json, text/plain",
        "text/html;q=1.0, application/json;q=0.9, */*;q=0.8",
        "text/html;q=0.9, application/json;q=0.5",
        "text/html, application/*;q=0.9, application/json;q=0.8",
        "text/html, application/json;q=1.0",
        "text/html,application/xhtml+xml,application/json;q=0.9,image/webp,*/*;q=0.8",
        "application/json;q=0.1, text/html;q=1.0",
    ],
)
@pytest.mark.asyncio
async def test_html_error(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    ziti_frontend_error_template_html_file: str,
    ziti_frontend_error_template_html: str,
    accept_header: str,
):
    template = Template(ziti_frontend_error_template_html)
    settings = settings_factory(
        frontend={
            "domain": "ext.mrok.test",
            "errors": {
                "502": {
                    "html": ziti_frontend_error_template_html_file,
                }
            },
        }
    )
    mocker.patch("mrok.frontend.app.get_settings", return_value=settings)
    m_send_error = mocker.patch.object(ProxyAppBase, "send_error_response")
    m_send = mocker.AsyncMock()
    scope = {
        "headers": [
            (b"accept", accept_header.encode("latin-1")),
        ],
    }

    app = FrontendProxyApp("my-identity")

    await app.send_error_response(
        {
            "headers": [
                (b"accept", accept_header.encode("latin-1")),
            ],
        },
        m_send,
        502,
        "bad gateway",
    )
    m_send_error.assert_awaited_once_with(
        scope,
        m_send,
        502,
        template.render({"status": 502, "body": "bad gateway"}),
        headers=[
            (b"content-type", b"text/html"),
        ],
    )


@pytest.mark.asyncio
async def test_html_error_no_html_template(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    settings = settings_factory(
        frontend={
            "domain": "ext.mrok.test",
            "errors": {
                "502": {
                    "xml": "/path/to/xml/template",
                }
            },
        }
    )
    mocker.patch("mrok.frontend.app.get_settings", return_value=settings)
    m_send_error = mocker.patch.object(ProxyAppBase, "send_error_response")
    m_send = mocker.AsyncMock()
    scope = {
        "headers": [
            (b"accept", b"text/html"),
        ],
    }

    app = FrontendProxyApp("my-identity")

    await app.send_error_response(
        {
            "headers": [
                (b"accept", b"text/html"),
            ],
        },
        m_send,
        502,
        "bad gateway",
    )
    m_send_error.assert_awaited_once_with(
        scope,
        m_send,
        502,
        "bad gateway",
    )


@pytest.mark.asyncio
async def test_html_error_no_accept(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    ziti_frontend_error_template_html_file: str,
):
    settings = settings_factory(
        frontend={
            "domain": "ext.mrok.test",
            "errors": {
                "502": {
                    "html": ziti_frontend_error_template_html_file,
                }
            },
        }
    )
    mocker.patch("mrok.frontend.app.get_settings", return_value=settings)
    m_send_error = mocker.patch.object(ProxyAppBase, "send_error_response")
    m_send = mocker.AsyncMock()
    scope = {
        "headers": [
            (b"host", b"localhost"),
        ],
    }

    app = FrontendProxyApp("my-identity")

    await app.send_error_response(
        {
            "headers": [
                (b"host", b"localhost"),
            ],
        },
        m_send,
        502,
        "bad gateway",
    )
    m_send_error.assert_awaited_once_with(
        scope,
        m_send,
        502,
        "bad gateway",
    )


@pytest.mark.parametrize(
    "accept_header",
    [
        "application/json",
        "application/json, text/javascript, */*",
        "text/html;q=0.9, application/json;q=1.0, text/plain;q=0.5",
        "application/json;q=0.8, application/xml;q=0.8",
        "application/json, application/*;q=0.9, */*;q=0.8",
        "application/json, text/plain, */*;q=0.01",
        "application/json;q=0.1, text/html;q=0",
        "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=1.0",
    ],
)
@pytest.mark.asyncio
async def test_json_error(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    ziti_frontend_error_template_json_file: str,
    ziti_frontend_error_template_json: str,
    accept_header: str,
):
    template = Template(ziti_frontend_error_template_json)
    settings = settings_factory(
        frontend={
            "domain": "ext.mrok.test",
            "errors": {
                "502": {
                    "json": ziti_frontend_error_template_json_file,
                }
            },
        }
    )
    mocker.patch("mrok.frontend.app.get_settings", return_value=settings)
    m_send_error = mocker.patch.object(ProxyAppBase, "send_error_response")
    m_send = mocker.AsyncMock()
    scope = {
        "headers": [
            (b"accept", accept_header.encode("latin-1")),
        ],
    }

    app = FrontendProxyApp("my-identity")

    await app.send_error_response(
        {
            "headers": [
                (b"accept", accept_header.encode("latin-1")),
            ],
        },
        m_send,
        502,
        "bad gateway",
    )
    m_send_error.assert_awaited_once_with(
        scope,
        m_send,
        502,
        template.render({"status": 502, "body": "bad gateway"}),
        headers=[
            (b"content-type", b"application/json"),
        ],
    )
