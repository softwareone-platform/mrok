from abc import ABC, abstractmethod
from typing import Any

from dynaconf import DataDict
from pydantic import BaseModel

from mrok.authentication.credentials import Credentials
from mrok.types.proxy import Scope


class AuthIdentity(BaseModel):
    subject: str
    scopes: list[str] = []
    metadata: dict[str, Any] = {}


class AuthenticationError(Exception):
    pass


class BaseHTTPAuthBackend(ABC):
    """
    Framework-agnostic HTTP authentication backend.

    """

    def __init__(self, config: DataDict):
        self.config = config

    @abstractmethod
    def get_credentials(self, scope: Scope) -> Credentials | None:
        raise NotImplementedError()

    @abstractmethod
    async def authenticate(self, credentials: Credentials) -> AuthIdentity | None:
        raise NotImplementedError()
