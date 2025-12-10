import pytest
from pytest_mock import MockerFixture

from mrok.proxy.app import ProxyApp, ProxyError
from tests.conftest import SettingsFactory

pytestmark = pytest.mark.skipif()


def test_init(mocker: MockerFixture):
    ziti_conn_mgr_ctor = mocker.patch("mrok.proxy.app.ZitiConnectionManager")

    ProxyApp("my-identity.json")

    ziti_conn_mgr_ctor.assert_called_once_with(
        "my-identity.json",
        ttl_seconds=60,
        purge_interval=10,
    )


def test_init_with_kw(mocker: MockerFixture):
    ziti_conn_mgr_ctor = mocker.patch("mrok.proxy.app.ZitiConnectionManager")

    app = ProxyApp(
        "my-identity.json",
        read_chunk_size=500,
        ziti_connection_ttl_seconds=5,
        ziti_conn_cache_purge_interval_seconds=1,
    )
    assert app._read_chunk_size == 500
    ziti_conn_mgr_ctor.assert_called_once_with(
        "my-identity.json",
        ttl_seconds=5,
        purge_interval=1,
    )


@pytest.mark.parametrize("wildcard_domain", ["exts.s1.today", ".exts.s1.today"])
@pytest.mark.parametrize("header_name", ["x-forwarded-for", "host"])
@pytest.mark.parametrize(
    ("hostname", "expected_target"),
    [
        ("ext-1234-5678.exts.s1.today", "ext-1234-5678"),
        ("ins-1234-5678-0001.ext-1234-5678.exts.s1.today", "ins-1234-5678-0001.ext-1234-5678"),
        ("ext-1234-5678.exts.s1.today:3322", "ext-1234-5678"),
        ("ins-1234-5678-0001.ext-1234-5678.exts.s1.today:1234", "ins-1234-5678-0001.ext-1234-5678"),
    ],
)
def test_get_target_name(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    wildcard_domain: str,
    hostname: str,
    header_name: str,
    expected_target: str,
):
    mocker.patch("mrok.proxy.app.ZitiConnectionManager")
    mocker.patch(
        "mrok.proxy.app.get_settings",
        return_value=settings_factory(proxy={"domain": wildcard_domain}),
    )
    app = ProxyApp("my-identity.json")
    assert app.get_target_name({header_name: hostname}) == expected_target


def test_get_target_name_no_headers(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
):
    mocker.patch("mrok.proxy.app.ZitiConnectionManager")
    mocker.patch("mrok.proxy.app.get_settings", return_value=settings_factory())
    app = ProxyApp("my-identity.json")
    with pytest.raises(ProxyError) as cv:
        app.get_target_name({})

    assert str(cv.value) == (
        "Cannot determine the target OpenZiti service/terminator name, "
        "neither Host nor X-Forwarded-For headers have been sent in the request."
    )


@pytest.mark.parametrize("x_fwd_for", ["localhost", "ext-1234-5678.example.com"])
def test_get_target_name_invalid_value(
    mocker: MockerFixture,
    settings_factory: SettingsFactory,
    x_fwd_for: str,
):
    mocker.patch("mrok.proxy.app.ZitiConnectionManager")
    mocker.patch("mrok.proxy.app.get_settings", return_value=settings_factory())
    app = ProxyApp("my-identity.json")
    with pytest.raises(ProxyError) as cv:
        app.get_target_name({"x-forwarded-for": x_fwd_for})

    assert str(cv.value) == (f"Unexpected value for Host or X-Forwarded-For header: `{x_fwd_for}`.")


@pytest.mark.asyncio
async def test_select_backend(mocker: MockerFixture, settings_factory: SettingsFactory):
    mocked_conn_mgr = mocker.AsyncMock()
    mocked_reader = mocker.MagicMock()
    mocked_writer = mocker.MagicMock()
    mocked_conn_mgr.get.return_value = (mocked_reader, mocked_writer)
    mocker.patch("mrok.proxy.app.ZitiConnectionManager", return_value=mocked_conn_mgr)
    mocker.patch(
        "mrok.proxy.app.get_settings",
        return_value=settings_factory(proxy={"domain": "exts.s1.cool"}),
    )

    app = ProxyApp("my-identity.json")
    reader, writer = await app.select_backend({}, {"x-forwarded-for": "ext-1234.exts.s1.cool"})
    assert reader == mocked_reader
    assert writer == mocked_writer
    mocked_conn_mgr.get.assert_awaited_once_with("ext-1234")
