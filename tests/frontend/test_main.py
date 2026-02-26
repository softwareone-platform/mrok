from pytest_mock import MockerFixture

from mrok.frontend.main import run


def test_run(mocker: MockerFixture):
    mocker.patch(
        "mrok.frontend.main.get_logging_config",
        return_value={"logging": "config"},
    )

    mock_settings = mocker.MagicMock()
    mock_settings.controller.auth = {"backends": []}
    mocker.patch("mrok.frontend.main.get_settings", return_value=mock_settings)

    m_app = mocker.MagicMock()
    m_standalone_app = mocker.patch("mrok.frontend.main.StandaloneApplication", return_value=m_app)

    run("my-identity.json", "localhost", 2423, 4, False, 1001, 323, 99.5)

    assert m_standalone_app.mock_calls[0].args[0]["bind"] == "localhost:2423"
    assert m_standalone_app.mock_calls[0].args[0]["workers"] == 4
    assert (
        m_standalone_app.mock_calls[0].args[0]["worker_class"]
        == "mrok.frontend.main.MrokUvicornWorker"
    )
    assert m_standalone_app.mock_calls[0].args[0]["logconfig_dict"] == {"logging": "config"}
    assert m_standalone_app.mock_calls[0].args[0]["reload"] is False
    assert m_standalone_app.mock_calls[0].args[0]["mrok"]["identity_file"] == "my-identity.json"
    assert m_standalone_app.mock_calls[0].args[0]["mrok"]["max_connections"] == 1001
    assert m_standalone_app.mock_calls[0].args[0]["mrok"]["max_keepalive_connections"] == 323
    assert m_standalone_app.mock_calls[0].args[0]["mrok"]["keepalive_expiry"] == 99.5

    m_app.run.assert_called_once()
