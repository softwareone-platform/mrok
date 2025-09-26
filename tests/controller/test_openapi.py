from fastapi import FastAPI
from pytest_mock import MockerFixture

from mrok.controller.openapi import generate_openapi_spec
from tests.conftest import SettingsFactory


def test_gen_openapi(settings_factory: SettingsFactory, fastapi_app: FastAPI):
    settings = settings_factory()
    assert fastapi_app.openapi_schema is None
    spec = generate_openapi_spec(fastapi_app, settings)
    assert fastapi_app.openapi_schema == spec


def test_gen_openapi_already_generated(
    mocker: MockerFixture, settings_factory: SettingsFactory, fastapi_app: FastAPI
):
    mocked_spec = mocker.MagicMock()
    settings = settings_factory()
    fastapi_app.openapi_schema = mocked_spec
    spec = generate_openapi_spec(fastapi_app, settings)
    assert fastapi_app.openapi_schema == spec
