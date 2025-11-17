from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from mrok.agent.sidecar.store import RequestStore
from mrok.cli.commands.agent.utils import create_inspection_server, run_inspect_api, run_textual


def test_run_inspect_api(
    mocker: MockerFixture,
):
    mocked_uvicorn = mocker.patch("mrok.cli.commands.agent.utils.uvicorn.run")

    inspect_api = mocker.MagicMock(spec=FastAPI)
    mocked_create_server = mocker.patch(
        "mrok.cli.commands.agent.utils.create_inspection_server", return_value=inspect_api
    )

    store = RequestStore()

    run_inspect_api(store, 5051, "warning")

    mocked_uvicorn.assert_called_once_with(inspect_api, port=5051, log_level="warning")
    mocked_create_server.assert_called_once_with(store)


def test_run_textual(mocker: MockerFixture):
    mocked_serve = mocker.patch("mrok.cli.commands.agent.utils.MServer.serve")
    store = RequestStore()
    run_textual(4040, 5051, store)

    mocked_serve.assert_called_once()


def test_create_inspection_server_handler():
    store = RequestStore()
    store.add({"id": 1})
    store.add({"id": 2})
    store.add({"id": 3})

    app = create_inspection_server(store)
    client = TestClient(app)

    resp = client.get("/requests/")
    resp_with_offset = client.get("/requests/?offset=1")

    assert resp.status_code == 200
    assert len(resp.json()) == 3

    assert resp_with_offset.status_code == 200
    assert len(resp_with_offset.json()) == 2
