import logging

import pytest
from pytest_mock import MockerFixture

from mrok.frontend.logging import request_target, setup_log_record_factory
from mrok.logging import ACCESS_LOG_FORMAT, get_logging_config
from tests.types import SettingsFactory


def _install_factory(mocker: MockerFixture):
    m_set_factory = mocker.patch("logging.setLogRecordFactory")
    setup_log_record_factory()
    return m_set_factory.call_args.args[0]


def test_log_record_factory_sets_request_target(mocker: MockerFixture):
    factory = _install_factory(mocker)

    token = request_target.set("ext-1234-5678")
    try:
        record = factory("uvicorn.access", logging.INFO, __file__, 1, "msg", (), None)
    finally:
        request_target.reset(token)

    assert isinstance(record, logging.LogRecord)
    assert record.request_target == "ext-1234-5678"


def test_log_record_factory_without_request_target(mocker: MockerFixture):
    factory = _install_factory(mocker)

    record = factory("uvicorn.access", logging.INFO, __file__, 1, "msg", (), None)

    assert record.request_target == "-"


@pytest.mark.parametrize(
    ("rich", "expected_handler"),
    [(False, "access"), (True, "rich")],
)
def test_get_logging_config_access_handler(
    settings_factory: SettingsFactory, rich: bool, expected_handler: str
):
    settings = settings_factory(logging={"debug": True, "rich": rich})

    config = get_logging_config(settings)

    assert config["loggers"]["gunicorn.access"]["handlers"] == [expected_handler]
    assert config["loggers"]["uvicorn.access"]["handlers"] == [expected_handler]
    assert config["formatters"]["access"] == {
        "format": ACCESS_LOG_FORMAT,
        "style": "{",
        "defaults": {"request_target": "-"},
    }
