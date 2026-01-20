from abc import ABC, abstractmethod
from typing import Any

from dynaconf.utils.boxing import DynaBox
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBase
from pydantic import BaseModel

UNAUTHORIZED_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized."
)


class AuthIdentity(BaseModel):
    subject: str
    scopes: list[str] = []
    metadata: dict[str, Any] = {}


class BaseHTTPAuthBackend(ABC):
    def __init__(self, config: DynaBox):
        self.config = config
        self.scheme = self.init_scheme()

    @abstractmethod
    def init_scheme(self) -> HTTPBase:
        raise NotImplementedError()

    @abstractmethod
    async def authenticate(self, credentials: HTTPAuthorizationCredentials) -> AuthIdentity | None:
        raise NotImplementedError()

    async def __call__(self, request: Request) -> AuthIdentity | None:
        credentials = await self.scheme(request)
        if not credentials:
            return None
        return await self.authenticate(credentials)
