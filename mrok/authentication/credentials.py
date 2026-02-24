from abc import ABC, abstractmethod
from dataclasses import dataclass

from mrok.proxy.models import HTTPHeaders
from mrok.types.proxy import Scope


@dataclass
class Credentials(ABC):
    credentials: str

    @classmethod
    @abstractmethod
    def extract_from_asgi_scope(cls, scope: Scope):
        pass  # pragma: no cover


class BearerCredentials(Credentials):
    @classmethod
    def extract_from_asgi_scope(cls, scope: Scope):
        headers = HTTPHeaders.from_asgi(scope.get("headers", []))
        authorization = headers.get("authorization", "")
        schema, _, value = authorization.partition(" ")
        if schema.lower() != "bearer" or not value:
            return None
        return cls(credentials=value.strip())
