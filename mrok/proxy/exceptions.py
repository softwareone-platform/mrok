from http import HTTPStatus

from httpcore import ConnectError


class ProxyError(Exception):
    def __init__(self, http_status: HTTPStatus, message: str) -> None:
        self.http_status: HTTPStatus = http_status
        self.message: str = message


class InvalidTargetError(ProxyError):
    def __init__(self):
        super().__init__(HTTPStatus.BAD_GATEWAY, "Bad Gateway: invalid target extension.")


class TargetUnavailableError(ProxyError, ConnectError):
    def __init__(self):
        super().__init__(
            HTTPStatus.SERVICE_UNAVAILABLE,
            "Service Unavailable: the target extension is unavailable.",
        )
