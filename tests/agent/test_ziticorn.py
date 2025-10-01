from pytest_mock import MockerFixture

from mrok.agent import ziticorn


def test_run_ziticorn(mocker: MockerFixture):
    fake_app = mocker.MagicMock()

    mocked_config = mocker.MagicMock()
    mocked_config_ctor = mocker.patch(
        "mrok.agent.ziticorn.MrokBackendConfig",
        return_value=mocked_config,
    )

    mocked_server = mocker.MagicMock()
    mocked_server_ctor = mocker.patch(
        "mrok.agent.ziticorn.MrokServer",
        return_value=mocked_server,
    )

    ziticorn.run_ziticorn(fake_app, "ziti-identity.json")

    mocked_config_ctor.assert_called_once_with(fake_app, "ziti-identity.json")
    mocked_server_ctor.assert_called_once_with(mocked_config)
    mocked_server.run.assert_called_once()


def test_run(mocker: MockerFixture):
    fake_app = mocker.MagicMock()
    mocked_start_fn = mocker.MagicMock()
    mocked_partial = mocker.patch("mrok.agent.ziticorn.partial", return_value=mocked_start_fn)

    mocked_master = mocker.MagicMock()
    mocked_master_ctor = mocker.patch(
        "mrok.agent.ziticorn.Master",
        return_value=mocked_master,
    )

    ziticorn.run(fake_app, "ziti-identity.json", workers=10, reload=True)

    mocked_partial.assert_called_once_with(
        ziticorn.run_ziticorn,
        fake_app,
        "ziti-identity.json",
    )
    mocked_master_ctor.assert_called_once_with(mocked_start_fn, workers=10, reload=True)
    mocked_master.run.assert_called_once()
