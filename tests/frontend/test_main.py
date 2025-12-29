from pytest_mock import MockerFixture

from mrok.frontend.main import run


def test_run(mocker: MockerFixture):
    mocker.patch(
        "mrok.frontend.main.get_logging_config",
        return_value={"logging": "config"},
    )
    m_asgi_app = mocker.MagicMock()
    m_asgi_app_ctor = mocker.patch("mrok.frontend.main.FrontendProxyApp", return_value=m_asgi_app)
    m_app = mocker.MagicMock()
    m_standalone_app = mocker.patch("mrok.frontend.main.StandaloneApplication", return_value=m_app)
    run("my-identity.json", "localhost", 2423, 4, 1001, 323, 99.5)
    m_standalone_app.assert_called_once_with(
        m_asgi_app,
        {
            "bind": "localhost:2423",
            "workers": 4,
            "worker_class": "mrok.frontend.main.MrokUvicornWorker",
            "logconfig_dict": {"logging": "config"},
            "reload": False,
        },
    )
    m_app.run.assert_called_once()
    m_asgi_app_ctor.assert_called_once_with(
        "my-identity.json",
        max_connections=1001,
        max_keepalive_connections=323,
        keepalive_expiry=99.5,
    )
