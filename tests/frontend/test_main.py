from unittest.mock import call

from pytest_mock import MockerFixture

from mrok.frontend.asgi_auth_adapter import ASGIAuthenticationMiddleware
from mrok.frontend.main import run
from mrok.frontend.middleware import HealthCheckMiddleware


def test_run(mocker: MockerFixture):
    mocker.patch(
        "mrok.frontend.main.get_logging_config",
        return_value={"logging": "config"},
    )

    mock_settings = mocker.MagicMock()
    mock_settings.controller.auth = {"backends": []}
    mocker.patch("mrok.frontend.main.get_settings", return_value=mock_settings)

    m_auth_manager = mocker.MagicMock()
    m_auth_manager_ctor = mocker.patch(
        "mrok.frontend.main.HTTPAuthManager",
        return_value=m_auth_manager,
    )

    m_asgi_app = mocker.MagicMock()
    m_asgi_app_ctor = mocker.patch("mrok.frontend.main.FrontendProxyApp", return_value=m_asgi_app)

    m_wrapper = mocker.MagicMock(name="ASGIAppWrapper_instance")
    m_wrapper_ctor = mocker.patch(
        "mrok.frontend.main.ASGIAppWrapper",
        return_value=m_wrapper,
    )

    m_app = mocker.MagicMock()
    m_standalone_app = mocker.patch("mrok.frontend.main.StandaloneApplication", return_value=m_app)

    run("my-identity.json", "localhost", 2423, 4, 1001, 323, 99.5)

    m_asgi_app_ctor.assert_called_once_with(
        "my-identity.json",
        max_connections=1001,
        max_keepalive_connections=323,
        keepalive_expiry=99.5,
    )
    m_wrapper_ctor.assert_called_once_with(m_asgi_app)
    m_auth_manager_ctor.assert_called_once_with(mock_settings.controller.auth)

    assert m_wrapper.add_middleware.call_args_list == [
        call(HealthCheckMiddleware),
        call(
            ASGIAuthenticationMiddleware,
            auth_manager=m_auth_manager,
            exclude_paths={"/healthcheck"},
        ),
    ]
    assert m_wrapper.add_middleware.call_count == 2
    assert m_wrapper.add_middleware.call_args_list[1].kwargs["auth_manager"] is m_auth_manager

    args, _ = m_standalone_app.call_args
    wrapper_arg, options = args
    assert wrapper_arg is m_wrapper
    assert options["bind"] == "localhost:2423"
    assert options["workers"] == 4
    assert options["worker_class"] == "mrok.frontend.main.MrokUvicornWorker"
    assert options["logconfig_dict"] == {"logging": "config"}
    assert options["reload"] is False

    m_app.run.assert_called_once()
    m_app.run.assert_called_once()
