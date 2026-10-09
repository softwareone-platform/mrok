import contextvars
import logging

request_target: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_target", default=None
)


def setup_log_record_factory() -> None:
    default_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = default_factory(*args, **kwargs)
        record.request_target = request_target.get() or "-"
        return record

    logging.setLogRecordFactory(record_factory)
