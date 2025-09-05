import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from functools import cached_property
from types import TracebackType
from typing import Any, ClassVar, Self

import httpx

from app.conf import Settings

logger = logging.getLogger(__name__)


class APIClientError(Exception):
    client_name: ClassVar[str]

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.client_name = cls.__module__.split(".")[-1]

    def __init__(self, message: str):
        self.message = message

        super().__init__(f"{self.client_name} API client error: {message}")


class BaseAPIClient(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.limit = 50
        self.token = ""

    @property
    @abstractmethod
    def base_url(self):
        raise NotImplementedError("base_url property must be implemented in subclasses")

    @property
    @abstractmethod
    def auth(self):
        raise NotImplementedError("base_url property must be implemented in subclasses")

    @cached_property
    def httpx_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            auth=self.auth,
            verify=False,
            timeout=httpx.Timeout(
                connect=0.25,
                read=self.settings.api_client_read_timeout_seconds,
                write=2.0,
                pool=5.0,
            ),
        )

    async def collection_iterator(self, endpoint: str, params: dict[str, str] = None) -> AsyncGenerator[dict, None]:
        params = params or {}
        params["limit"] = self.limit
        params["offset"] = 0
        while True:
            page_response = await self.httpx_client.get(endpoint,params=params)
            page_response.raise_for_status()
            page = page_response.json()

            items = page["data"]

            for item in items:
                yield item

            pagination_meta = page["meta"]["pagination"]
            total = pagination_meta["totalCount"]
            if total <= self.limit + params["offset"]:
                break

            params["offset"] = params["offset"] + self.limit

    async def create(self, endpoint: str, data: dict) -> dict[str, Any]:
        response = await self.httpx_client.post(endpoint, json=data)
        response.raise_for_status()

        return response.json()["data"]

    async def __aenter__(self) -> Self:
        await self.httpx_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> None:
        return await self.httpx_client.__aexit__(exc_type, exc_val, exc_tb)


class BaseApiClientAuth(httpx.Auth):
    def __init__(self, client: BaseAPIClient):
        self.client = client

    def update_token(self, response: httpx.Response) -> None:
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            self.client.token = data["data"]["token"]
