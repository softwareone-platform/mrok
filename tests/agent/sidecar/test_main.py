import pytest
from pytest_mock import MockerFixture

from mrok.agent.sidecar import main


@pytest.mark.parametrize("target_addr", ["/path/to/unix.sock", ("localhost", 8080)])
def test_run_sidecar(mocker: MockerFixture, target_addr: str | tuple[str, int]):
    mocked_app = mocker.MagicMock()
    mocked_app_ctor = mocker.patch(
        "mrok.agent.sidecar.main.ForwardApp",
        return_value=mocked_app,
    )

    mocked_config = mocker.MagicMock()
    mocked_config_ctor = mocker.patch(
        "mrok.agent.sidecar.main.MrokBackendConfig",
        return_value=mocked_config,
    )

    mocked_server = mocker.MagicMock()
    mocked_server_ctor = mocker.patch(
        "mrok.agent.sidecar.main.MrokServer",
        return_value=mocked_server,
    )

    main.run_sidecar("ziti-identity.json", target_addr)

    mocked_config_ctor.assert_called_once_with(mocked_app, "ziti-identity.json")
    mocked_app_ctor.assert_called_once_with(target_addr)
    mocked_server_ctor.assert_called_once_with(mocked_config)
    mocked_server.run.assert_called_once()


def test_run(mocker: MockerFixture):
    mocked_start_fn = mocker.MagicMock()
    mocked_partial = mocker.patch("mrok.agent.sidecar.main.partial", return_value=mocked_start_fn)

    mocked_master = mocker.MagicMock()
    mocked_master_ctor = mocker.patch(
        "mrok.agent.sidecar.main.Master",
        return_value=mocked_master,
    )

    main.run("ziti-identity.json", "target-addr", workers=10, reload=True)

    mocked_partial.assert_called_once_with(
        main.run_sidecar,
        "ziti-identity.json",
        "target-addr",
    )
    mocked_master_ctor.assert_called_once_with(mocked_start_fn, workers=10, reload=True)
    mocked_master.run.assert_called_once()
