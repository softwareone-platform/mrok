from pytest_mock import MockerFixture

from mrok.proxy.asgi import ASGIAppWrapper
from mrok.proxy.middleware import CaptureMiddleware, MetricsMiddleware
from mrok.proxy.worker import Worker
from tests.types import SettingsFactory


def test_setup_app(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_app = mocker.AsyncMock()
    worker = Worker(
        "my-worker-id",
        m_app,
        ziti_identity_file,
    )
    app = worker.setup_app()
    assert isinstance(app, ASGIAppWrapper)
    assert worker._event_publisher is not None
    assert app.lifespan == worker._event_publisher.lifespan
    assert app.middlware[0].cls == MetricsMiddleware
    assert app.middlware[0].args[0] == worker._event_publisher._metrics_collector
    assert app.middlware[1].cls == CaptureMiddleware
    assert app.middlware[1].args[0] == worker._event_publisher.publish_response_event


def test_setup_app_events_disabled(
    mocker: MockerFixture,
    ziti_identity_file: str,
):
    m_app = mocker.AsyncMock()
    worker = Worker(
        "my-worker-id",
        m_app,
        ziti_identity_file,
        events_enabled=False,
    )
    app = worker.setup_app()
    assert isinstance(app, ASGIAppWrapper)
    assert app.lifespan is None

    assert app.middlware == []


def test_run(
    mocker: MockerFixture,
    ziti_identity_file: str,
    settings_factory: SettingsFactory,
):
    settings = settings_factory()
    mocker.patch("mrok.proxy.worker.get_settings", return_value=settings)
    m_setup_logging = mocker.patch("mrok.proxy.worker.setup_logging")

    m_mrokconfig = mocker.MagicMock()
    m_mrokconfig_ctor = mocker.patch("mrok.proxy.worker.BackendConfig", return_value=m_mrokconfig)

    m_server = mocker.MagicMock()
    m_server_ctor = mocker.patch("mrok.proxy.worker.Server", return_value=m_server)
    m_app = mocker.MagicMock()
    mocker.patch.object(Worker, "setup_app", return_value=m_app)

    worker = Worker(
        "my-worker-id",
        m_app,
        ziti_identity_file,
    )
    worker.run()

    m_setup_logging.assert_called_once_with(settings)
    m_mrokconfig_ctor.assert_called_once_with(m_app, ziti_identity_file)
    m_server_ctor.assert_called_once_with(m_mrokconfig)
    m_server.run.assert_called_once()
