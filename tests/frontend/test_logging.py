import logging

from mrok.logging import TargetContextFilter, request_target


def _access_record() -> logging.LogRecord:
    return logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s" %d',
        ("127.0.0.1:1234", "GET /api HTTP/1.1", 200),
        None,
    )


def test_target_context_filter_prefixes_message():
    record = _access_record()
    token = request_target.set("ext-1234-5678")
    try:
        assert TargetContextFilter().filter(record) is True
    finally:
        request_target.reset(token)

    assert record.target == "ext-1234-5678"
    assert record.getMessage() == '[ext-1234-5678] 127.0.0.1:1234 - "GET /api HTTP/1.1" 200'


def test_target_context_filter_without_target():
    record = _access_record()

    assert TargetContextFilter().filter(record) is True
    assert record.target == ""
    assert record.getMessage() == '127.0.0.1:1234 - "GET /api HTTP/1.1" 200'


def test_target_context_filter_is_idempotent():
    record = _access_record()
    token = request_target.set("ext-1234-5678")
    try:
        log_filter = TargetContextFilter()
        assert log_filter.filter(record) is True
        assert log_filter.filter(record) is True
    finally:
        request_target.reset(token)

    assert record.getMessage() == '[ext-1234-5678] 127.0.0.1:1234 - "GET /api HTTP/1.1" 200'
