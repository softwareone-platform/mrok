from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends

from mrok.controller.dependencies.conf import AppSettings
from mrok.ziti import api


class APIClientFactory[T: api.BaseZitiAPI]:
    def __init__(self, client_cls: type[T]):
        self.client_cls = client_cls

    async def __call__(self, settings: AppSettings) -> AsyncGenerator[T]:
        client = self.client_cls(settings)
        async with client:
            yield client


ZitiManagementAPI = Annotated[
    api.ZitiManagementAPI,
    Depends(APIClientFactory(api.ZitiManagementAPI)),
]
ZitiClientAPI = Annotated[
    api.ZitiClientAPI,
    Depends(APIClientFactory(api.ZitiClientAPI)),
]
