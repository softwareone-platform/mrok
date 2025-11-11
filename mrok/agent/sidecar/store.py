from collections import deque
from multiprocessing import Lock
from multiprocessing.managers import BaseManager

from mrok.conf import get_settings


class RequestStore:
    def __init__(self):
        settings = get_settings()
        self._requests = deque(maxlen=settings.sidecar.store_size)
        self._lock = Lock()
        self._request_counter = 1

    def add(self, request: dict) -> None:
        with self._lock:
            request["id"] = self._request_counter
            self._requests.appendleft(request)
            self._request_counter += 1

    def get_all(self, starting_from: int | None = None) -> list[dict]:
        with self._lock:
            if starting_from:
                return [request for request in self._requests if request["id"] >= starting_from]
            else:
                return list(self._requests)


class RequestStoreManager(BaseManager):
    pass
