from collections import deque
from multiprocessing import Lock
from multiprocessing.managers import BaseManager
from typing import Any

from mrok.conf import get_settings


class RequestStore:
    def __init__(self):
        settings = get_settings()
        self._requests = deque(maxlen=settings.sidecar.store_size)
        self._lock = Lock()
        self._request_counter = 1

    def add(self, request: dict[str, Any]) -> None:
        with self._lock:
            request["id"] = self._request_counter
            self._requests.appendleft(request)
            self._request_counter += 1

    def get_all(self, offset: int = 0) -> list[dict]:
        with self._lock:
            return [request for request in self._requests if request["id"] > offset]


class RequestStoreManager(BaseManager):
    pass
