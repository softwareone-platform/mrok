from pytest_mock import MockerFixture

from mrok.agent.sidecar.store import RequestStore
from tests.conftest import SettingsFactory


def test_request_store(
    settings_factory: SettingsFactory,
    mocker: MockerFixture,
):
    settings = settings_factory(sidecar={"store_size": 2})
    mocker.patch("mrok.agent.sidecar.store.get_settings", return_value=settings)
    store = RequestStore()

    assert len(store.get_all()) == 0

    store.add({"id": 1})
    store.add({"id": 2})

    assert len(store.get_all()) == 2

    store.add({"id": 3})

    assert len(store.get_all()) == 2
    assert len(store.get_all(offset=3)) == 0
