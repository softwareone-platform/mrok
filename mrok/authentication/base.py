from abc import ABC, abstractmethod
from typing import Any

from dynaconf.utils.boxing import DynaBox
from pydantic import BaseModel


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

    def __init__(self, config: DynaBox):
        self.config = config

    @abstractmethod
    async def authenticate(self, authorization: str | None) -> AuthIdentity | None:
        """
        Validate the Authorization header value.

        :param authorization: Raw Authorization header string.
        :return: AuthIdentity if valid, else None.
        """
        raise NotImplementedError()
